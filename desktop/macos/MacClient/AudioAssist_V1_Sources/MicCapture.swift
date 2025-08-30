import AVFoundation
import CoreAudio
import Foundation

/// Captures microphone audio input using AVAudioEngine
/// Handles device changes (AirPods connect/disconnect) with pop-free transitions
/// Converts audio to 16kHz mono Linear16 PCM for Deepgram Live API
class MicCapture {
    
    // MARK: - Properties
    
    private var audioEngine: AVAudioEngine?
    private var inputNode: AVAudioInputNode?
    private var audioConverter: AVAudioConverter?
    private var onPCMCallback: ((Data) -> Void)?
    
    private var isCapturing = false
    
    // TASK 1: Route change detection (macOS Core Audio)
    private var routeChangeObserver: NSObjectProtocol?
    private var inputDeviceListener: AudioObjectPropertyListenerProc?
    private var isMonitoringInputDevice = false
    
    // TASK 4: Race-safe restart guard
    private var isRestarting = false
    private var restartTask: Task<Void, Never>?
    
    // TASK 3: Device change callback
    var onDeviceChange: (() -> Void)?
    
    // TASK 8: Observability hooks
    var onMetric: ((String, Double, [String: String]) -> Void)?
    
    // TASK 5: Telemetry
    private var deviceChangeCount: Int = 0
    
    // TASK 7: Error handling & retry
    private var restartAttempts: Int = 0
    private let maxRestartAttempts: Int = 3
    
    // Device Change Coordinator
    private let deviceCoordinator = DeviceChangeCoordinator.shared
    private var coordinatorObserver: NSObjectProtocol?
    
    // Warm-up frames to avoid garbage during device settle
    private var warmUpFrames: Int = 0
    private let warmUpFrameCount: Int = 3  // Skip first 3 callbacks after restart
    
    // Target format: 16kHz, mono, PCM Int16 interleaved (standardized for Deepgram)
    // 🚨 FIXED: Standardized to 16kHz for consistent Deepgram quality
    private let targetSampleRate: Double = 16000.0
    private let targetChannels: UInt32 = 1
    private let bufferSize: UInt32 = 1024  // Smaller buffer for 16kHz (~64ms at 16kHz)
    
    // MARK: - Initialization
    
    init() {
        print("[DEBUG] MicCapture initialized")
        setupDeviceCoordinator()
        // No audio session setup needed on macOS
    }
    
    deinit {
        stop()
        removeAudioSessionNotifications()
        removeDeviceCoordinator()
        restartTask?.cancel()
        print("[DEBUG] MicCapture deinitialized")
    }
    
    // MARK: - Device Change Coordinator
    
    /// Setup DeviceChangeCoordinator integration
    private func setupDeviceCoordinator() {
        // Listen for coordinator restart notifications
        coordinatorObserver = NotificationCenter.default.addObserver(
            forName: NSNotification.Name("DeviceCoordinatorMicRestart"),
            object: nil,
            queue: .main
        ) { [weak self] _ in
            self?.performCoordinatedRestart()
        }
        
        print("[DEBUG] 🎛️ DeviceChangeCoordinator integration setup")
    }
    
    /// Remove DeviceChangeCoordinator integration
    private func removeDeviceCoordinator() {
        if let observer = coordinatorObserver {
            NotificationCenter.default.removeObserver(observer)
            coordinatorObserver = nil
        }
        
        print("[DEBUG] 🎛️ DeviceChangeCoordinator integration removed")
    }
    
    /// Perform restart requested by DeviceChangeCoordinator
    private func performCoordinatedRestart() {
        print("[DEBUG] 🔄 [MIC] Performing coordinated restart...")
        
        // Store callback to restore after restart
        let callback = onPCMCallback
        
        // Reset warm-up counter for new device
        warmUpFrames = 0
        
        // Complete cleanup before restart
        print("[DEBUG] 🔄 [MIC] Performing complete cleanup...")
        
        // Remove tap first to prevent crashes
        inputNode?.removeTap(onBus: 0)
        
        // Stop and reset audio engine completely
        audioEngine?.stop()
        audioEngine?.reset()
        
        // Clear all references
        audioEngine = nil
        inputNode = nil
        audioConverter = nil
        isCapturing = false
        
        print("[DEBUG] 🔄 [MIC] Cleanup completed, waiting for device to settle...")
        
        // Brief delay to allow device to settle
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
            // Restore callback
            self.onPCMCallback = callback
            
            // Restart audio capture
            self.startAudioCapture()
            
            print("[DEBUG] 🔄 [MIC] Coordinated restart completed")
        }
    }
    
    // MARK: - Public API
    
    /// Start microphone capture with PCM callback
    /// - Parameter onPCM16k: Callback that receives 16kHz mono Linear16 PCM data
    func start(onPCM16k: @escaping (Data) -> Void) {
        print("[DEBUG] 🎤 MicCapture.start() called")
        
        guard !isCapturing else {
            print("[DEBUG] ⚠️ MicCapture already running")
            return
        }
        
        // Store callback
        self.onPCMCallback = onPCM16k
        
        // TASK 1: Setup audio session notifications
        setupAudioSessionNotifications()
        
        // On macOS, directly start audio capture (no permission dialog needed for microphone in non-sandboxed apps)
        startAudioCapture()
    }
    
    /// Stop microphone capture
    func stop() {
        print("[DEBUG] 🛑 MicCapture.stop() called")
        
        guard isCapturing else {
            print("[DEBUG] ⚠️ MicCapture already stopped")
            return
        }
        
        stopAudioCapture()
        removeAudioSessionNotifications()
    }
    
    // MARK: - Private Methods
    
    private func startAudioCapture() {
        print("[DEBUG] 🚀 Starting audio capture")
        
        // 🚨 FIXED: Ensure clean state before starting
        guard !isCapturing else {
            print("[DEBUG] ⚠️ Audio capture already active, skipping")
            return
        }
        
        // Create audio engine
        audioEngine = AVAudioEngine()
        
        guard let audioEngine = audioEngine else {
            print("[DEBUG] ❌ Failed to create AVAudioEngine")
            return
        }
        
        // Get input node
        inputNode = audioEngine.inputNode
        
        guard let inputNode = inputNode else {
            print("[DEBUG] ❌ Failed to get input node")
            return
        }
        
        // Get input format
        let inputFormat = inputNode.outputFormat(forBus: 0)
        print("[DEBUG] 📊 Input format: \(inputFormat)")
        print("[DEBUG] 📊 Input sample rate: \(inputFormat.sampleRate) Hz")
        print("[DEBUG] 📊 Input channels: \(inputFormat.channelCount)")
        print("[DEBUG] 📊 Input format description: \(inputFormat.formatDescription)")
        
        // 🚨 FIXED: Validate input format before proceeding
        guard inputFormat.sampleRate > 0 && inputFormat.channelCount > 0 else {
            print("[DEBUG] ❌ Invalid input format: sampleRate=\(inputFormat.sampleRate), channels=\(inputFormat.channelCount)")
            cleanup()
            return
        }
        
        // Create converter
        audioConverter = makeConverter(from: inputFormat)
        
        guard let converter = audioConverter else {
            print("[DEBUG] ❌ Failed to create audio converter for format: \(inputFormat)")
            print("[DEBUG] ❌ Input format details - Rate: \(inputFormat.sampleRate), Channels: \(inputFormat.channelCount), CommonFormat: \(inputFormat.commonFormat.rawValue)")
            cleanup()
            return
        }
        
        print("[DEBUG] ✅ Audio converter created successfully for input format: \(inputFormat.sampleRate)Hz, \(inputFormat.channelCount)ch")
        print("[DEBUG] ✅ Converter input format: \(converter.inputFormat)")
        print("[DEBUG] ✅ Converter output format: \(converter.outputFormat)")
        
        // 🚨 FIXED: Install tap with error handling
        do {
            // Remove any existing tap first
            inputNode.removeTap(onBus: 0)
            
            // Install new tap
            inputNode.installTap(onBus: 0, bufferSize: bufferSize, format: inputFormat) { [weak self] buffer, time in
                self?.processAudioBuffer(buffer, at: time)
            }
            
            print("[DEBUG] ✅ Audio tap installed successfully")
        } catch {
            print("[DEBUG] ❌ Failed to install audio tap: \(error.localizedDescription)")
            cleanup()
            return
        }
        
        // Start audio engine
        do {
            try audioEngine.start()
            isCapturing = true
            print("[DEBUG] ✅ Audio engine started successfully")
            print("[DEBUG] 🎤 Microphone capture is now active")
        } catch {
            print("[DEBUG] ❌ Failed to start audio engine: \(error.localizedDescription)")
            print("[DEBUG] ❌ Error details: \(error)")
            cleanup()
        }
    }
    
    private func stopAudioCapture() {
        print("[DEBUG] 🛑 Stopping audio capture")
        
        // Remove tap
        inputNode?.removeTap(onBus: 0)
        
        // Stop audio engine
        audioEngine?.stop()
        
        cleanup()
        
        print("[DEBUG] ✅ Audio capture stopped")
    }
    
    private func cleanup() {
        isCapturing = false
        audioEngine = nil
        inputNode = nil
        audioConverter = nil
        onPCMCallback = nil
    }
    
    // MARK: - Audio Processing
    
    private func processAudioBuffer(_ buffer: AVAudioPCMBuffer, at time: AVAudioTime) {
        guard let audioConverter = audioConverter else {
            print("[DEBUG] ⚠️ Audio converter not available")
            return
        }
        
        print("[DEBUG] 🎵 Processing audio buffer: \(buffer.frameLength) frames")
        
        // Check for warm-up period to avoid garbage frames during device settle
        if warmUpFrames < warmUpFrameCount {
            warmUpFrames += 1
            print("[DEBUG] 🔥 MIC warm-up drop (\(warmUpFrames)/\(warmUpFrameCount))")
            return
        }
        
        // Convert audio chunk to 16kHz mono PCM Int16
        if let pcmData = convertChunk(buffer, using: audioConverter) {
            // Debug PCM data
            if pcmData.count >= 4 {
                let samples = pcmData.withUnsafeBytes { bytes in
                    Array(bytes.bindMemory(to: Int16.self).prefix(2))
                }
                print("[DEBUG] 📊 Converted PCM Preview: \(samples) (first 2 samples)")
            }
            
            // Send PCM data via callback (only if not paused by coordinator)
            if !deviceCoordinator.shouldPausePCM() {
                onPCMCallback?(pcmData)
                
                // If this is the first valid buffer after restart, resume coordinator
                if deviceCoordinator.isRestartInProgress() {
                    print("[DEBUG] 🎤 First valid buffer received, resuming coordinator")
                    deviceCoordinator.resumeAll()
                }
            } else {
                print("[DEBUG] ⏸️ PCM callback paused by coordinator")
            }
            
            print("[DEBUG] 📤 Processed audio chunk: \(pcmData.count) bytes (\(pcmData.count / 2) samples)")
        } else {
            print("[DEBUG] ⚠️ Failed to convert audio chunk")
        }
    }
    
    // MARK: - Helper Functions
    
    /// Creates an AVAudioConverter from input format to target format (16kHz mono PCM Int16)
    /// - Parameter inputFormat: The source audio format
    /// - Returns: Configured AVAudioConverter or nil if creation fails
    private func makeConverter(from inputFormat: AVAudioFormat) -> AVAudioConverter? {
        print("[DEBUG] 🔄 Creating audio converter")
        
        // Create target format: 16kHz, mono, PCM Int16 interleaved
        guard let targetFormat = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: targetSampleRate,
            channels: targetChannels,
            interleaved: true
        ) else {
            print("[DEBUG] ❌ Failed to create target audio format")
            return nil
        }
        
        print("[DEBUG] 📊 Target format: \(targetFormat)")
        print("[DEBUG] 📊 Target sample rate: \(targetFormat.sampleRate) Hz")
        print("[DEBUG] 📊 Target channels: \(targetFormat.channelCount)")
        print("[DEBUG] 📊 Target format description: \(targetFormat.formatDescription)")
        
        // Create converter
        guard let converter = AVAudioConverter(from: inputFormat, to: targetFormat) else {
            print("[DEBUG] ❌ Failed to create AVAudioConverter")
            return nil
        }
        
        print("[DEBUG] ✅ Audio converter created successfully")
        return converter
    }
    
    /// Converts an audio buffer chunk using the provided converter
    /// - Parameters:
    ///   - buffer: Input audio buffer
    ///   - converter: AVAudioConverter to use for conversion
    /// - Returns: Converted PCM data as Data or nil if conversion fails
    private func convertChunk(_ buffer: AVAudioPCMBuffer, using converter: AVAudioConverter) -> Data? {
        // Calculate output buffer size
        let outputCapacity = AVAudioFrameCount(Double(buffer.frameLength) * targetSampleRate / buffer.format.sampleRate)
        
        // Create output buffer
        guard let outputBuffer = AVAudioPCMBuffer(
            pcmFormat: converter.outputFormat,
            frameCapacity: outputCapacity
        ) else {
            print("[DEBUG] ❌ Failed to create output buffer")
            return nil
        }
        
        // Convert audio
        var error: NSError?
        let status = converter.convert(to: outputBuffer, error: &error) { _, outStatus in
            outStatus.pointee = .haveData
            return buffer
        }
        
        if status == .error {
            print("[DEBUG] ❌ Audio conversion error: \(error?.localizedDescription ?? "Unknown error")")
            return nil
        }
        
        // Extract PCM data from buffer
        guard let channelData = outputBuffer.int16ChannelData?[0] else {
            print("[DEBUG] ❌ Failed to get channel data")
            return nil
        }
        
        let frameCount = Int(outputBuffer.frameLength)
        
        // Create Data from Int16 samples
        var data = Data(capacity: frameCount * MemoryLayout<Int16>.size)
        
        // Ensure little-endian byte order for Deepgram compatibility
        for i in 0..<frameCount {
            let sample = channelData[i]
            let littleEndianSample = sample.littleEndian
            
            // Convert Int16 to bytes (little-endian)
            let byte1 = UInt8(littleEndianSample & 0xFF)
            let byte2 = UInt8((littleEndianSample >> 8) & 0xFF)
            
            data.append(byte1)
            data.append(byte2)
        }
        
        return data
    }
    
    // MARK: - TASK 1: Audio Session Route Change Detection
    
    /// Setup Core Audio input device change notifications (macOS)
    private func setupAudioSessionNotifications() {
        // Remove existing observer if any
        removeAudioSessionNotifications()
        
        // macOS: Monitor default input device changes using Core Audio
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDefaultInputDevice,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        
        let listenerProc: AudioObjectPropertyListenerProc = { (objectID, numAddresses, addresses, clientData) in
            guard let clientData = clientData else { return noErr }
            let capture = Unmanaged<MicCapture>.fromOpaque(clientData).takeUnretainedValue()
            capture.handleInputDeviceChange()
            return noErr
        }
        
        let clientData = Unmanaged.passUnretained(self).toOpaque()
        let status = AudioObjectAddPropertyListener(
            AudioObjectID(kAudioObjectSystemObject),
            &address,
            listenerProc,
            clientData
        )
        
        if status == noErr {
            inputDeviceListener = listenerProc
            isMonitoringInputDevice = true
            print("[DEBUG] 🎧 Core Audio input device change notifications setup")
        } else {
            print("[DEBUG] ❌ Failed to setup input device listener: \(status)")
        }
    }
    
    /// Remove Core Audio input device change notifications (macOS)
    private func removeAudioSessionNotifications() {
        guard isMonitoringInputDevice, let listener = inputDeviceListener else {
            return
        }
        
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDefaultInputDevice,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        
        let clientData = Unmanaged.passUnretained(self).toOpaque()
        let status = AudioObjectRemovePropertyListener(
            AudioObjectID(kAudioObjectSystemObject),
            &address,
            listener,
            clientData
        )
        
        if status == noErr {
            print("[DEBUG] 🎧 Core Audio input device change notifications removed")
        } else {
            print("[DEBUG] ⚠️ Failed to remove input device listener: \(status)")
        }
        
        inputDeviceListener = nil
        isMonitoringInputDevice = false
    }
    
    /// Handle Core Audio input device change notifications (macOS)
    private func handleInputDeviceChange() {
        print("[DEBUG] 🎧 Input device change detected")
        
        // Get current default input device to verify change
        var deviceID: AudioDeviceID = 0
        var size = UInt32(MemoryLayout<AudioDeviceID>.size)
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDefaultInputDevice,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        
        let status = AudioObjectGetPropertyData(
            AudioObjectID(kAudioObjectSystemObject),
            &address, 0, nil, &size, &deviceID
        )
        
        if status == noErr {
            print("[DEBUG] 🎧 New input device ID: \(deviceID)")
            
            // 🚨 FIXED: Get device name for better logging
            let deviceName = getDeviceName(deviceID: deviceID)
            print("[DEBUG] 🎧 New input device: \(deviceName)")
            
            // 🚨 FIXED: Check if format changed before restarting
            if let currentFormat = getCurrentInputFormat() {
                print("[DEBUG] 🎧 New device format: \(currentFormat.sampleRate)Hz, \(currentFormat.channelCount)ch")
                
                // Use DeviceChangeCoordinator for coordinated restart
                deviceCoordinator.requestMicRestart(reason: "Input device changed to \(deviceName)")
            } else {
                print("[DEBUG] ❌ Failed to get new device format")
                deviceCoordinator.requestMicRestart(reason: "Input device changed (format unknown)")
            }
        } else {
            print("[DEBUG] ❌ Failed to get new input device: \(status)")
            deviceCoordinator.requestMicRestart(reason: "Input device change (device query failed)")
        }
    }
    
    /// Get the current input format from the audio engine
    private func getCurrentInputFormat() -> AVAudioFormat? {
        return inputNode?.outputFormat(forBus: 0)
    }
    
    /// Get device name for logging
    private func getDeviceName(deviceID: AudioDeviceID) -> String {
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioDevicePropertyDeviceNameCFString,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        
        var size: UInt32 = 0
        var status = AudioObjectGetPropertyDataSize(deviceID, &address, 0, nil, &size)
        guard status == noErr else { return "Unknown Device" }
        
        var name: CFString?
        status = AudioObjectGetPropertyData(deviceID, &address, 0, nil, &size, &name)
        guard status == noErr, let deviceName = name else { return "Unknown Device" }
        
        return deviceName as String
    }
    
    // MARK: - TASK 4: Race-safe Restart with Debounce
    
    /// Restart audio capture with debounce to prevent multiple rapid restarts
    private func restartAudioCaptureWithDebounce() {
        guard !isRestarting else {
            print("[DEBUG] 🎧 Restart already in progress, ignoring")
            return
        }
        
        isRestarting = true
        
        // Cancel any existing restart task
        restartTask?.cancel()
        
        restartTask = Task {
            // TASK 4: Debounce delay (300ms)
            try? await Task.sleep(nanoseconds: 300_000_000)
            
            await MainActor.run {
                self.performRestart()
                self.isRestarting = false
            }
        }
    }
    
    /// Perform the actual restart operation
    private func performRestart() {
        // TASK 5: Increment device change counter
        deviceChangeCount += 1
        print("[DEBUG] 🔄 [MIC] Restarting due to device change (count: \(deviceChangeCount))")
        
        // TASK 5: Telemetry - measure restart time
        let startTime = CFAbsoluteTimeGetCurrent()
        
        // Store callback to restore after restart
        let callback = onPCMCallback
        
        // 🚨 FIXED: Complete cleanup before restart
        print("[DEBUG] 🔄 [MIC] Performing complete cleanup...")
        
        // Remove tap first to prevent crashes
        inputNode?.removeTap(onBus: 0)
        
        // Stop and reset audio engine completely
        audioEngine?.stop()
        audioEngine?.reset()  // 🚨 FIXED: Reset engine state
        
        // Clear all references
        audioEngine = nil
        inputNode = nil
        audioConverter = nil
        isCapturing = false
        
        print("[DEBUG] 🔄 [MIC] Cleanup completed, waiting for device to settle...")
        
        // Brief delay to allow device to settle
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {  // 🚨 FIXED: Longer delay for AirPods
            // Restore callback
            self.onPCMCallback = callback
            
            // TASK 7: Attempt restart with error handling
            self.performRestartWithRetry()
            
            // TASK 5: Log restart time
            let restartTime = (CFAbsoluteTimeGetCurrent() - startTime) * 1000
            print("[DEBUG] 🔄 [MIC] Restart completed in \(Int(restartTime))ms")
            
            // TASK 8: Send metric
            self.onMetric?("mic_restart_ms", restartTime, [
                "device_type": "microphone",
                "change_count": "\(self.deviceChangeCount)"
            ])
        }
    }
    
    // MARK: - TASK 7: Error Handling & Retry Logic
    
    /// Perform restart with retry logic and fallback
    private func performRestartWithRetry() {
        guard restartAttempts < maxRestartAttempts else {
            print("[DEBUG] ❌ [MIC] Max restart attempts (\(maxRestartAttempts)) reached")
            fallbackToBuiltInDevice()
            return
        }
        
        restartAttempts += 1
        print("[DEBUG] 🔄 [MIC] Restart attempt \(restartAttempts)/\(maxRestartAttempts)")
        
        // Attempt to restart
        startAudioCapture()
        
        // Check if restart was successful
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            if self.isCapturing {
                // Success - reset attempt counter
                self.restartAttempts = 0
                self.onDeviceChange?()
                print("[DEBUG] ✅ [MIC] Restart successful")
            } else {
                // Failed - retry with exponential backoff
                let backoffDelay = Double(self.restartAttempts) * 0.5 // 0.5s, 1s, 1.5s
                print("[DEBUG] ⚠️ [MIC] Restart failed, retrying in \(backoffDelay)s")
                
                DispatchQueue.main.asyncAfter(deadline: .now() + backoffDelay) {
                    self.performRestartWithRetry()
                }
            }
        }
    }
    
    /// Fallback to built-in microphone device
    private func fallbackToBuiltInDevice() {
        print("[DEBUG] 🔄 [MIC] Falling back to built-in microphone")
        
        // Reset attempt counter
        restartAttempts = 0
        
        // Try to restart with built-in device (AVAudioEngine should automatically select available device)
        startAudioCapture()
        
        // Notify upper layers
        onDeviceChange?()
        
        print("[DEBUG] 🎤 [MIC] Fallback to built-in device completed")
    }
}
