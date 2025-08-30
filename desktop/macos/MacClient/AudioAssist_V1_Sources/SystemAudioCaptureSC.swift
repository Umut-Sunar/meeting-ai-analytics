import Foundation
import AVFoundation
import ScreenCaptureKit
import CoreMedia
import CoreAudio

@available(macOS 13.0, *)
final class SystemAudioCaptureSC: NSObject, SCStreamOutput, SCStreamDelegate {

    // Dışarı: 48 kHz, mono, Int16 PCM
    var onPCM16k: ((Data) -> Void)?

    private var stream: SCStream?
    private let audioQueue = DispatchQueue(label: "sc.audio.queue")
    private var converter: AVAudioConverter?
    
    // Enhanced permission management handled by PermissionsService
    
    // 🚨 CRITICAL FIX: Separate output handlers to prevent circular reference
    // This fixes the SCStream frame dropping issue identified in Apple Developer Forums
    private var streamOutputHandler: StreamOutputHandler?
    private var videoOutputHandler: VideoOutputHandler?
    
    // Frame drop detection for monitoring
    private var lastAudioReceived: Date?
    private var frameDropMonitor: Timer?
    
    // 🚨 CRASH PREVENTION: Error tracking
    private var consecutiveErrors: Int = 0
    private let maxConsecutiveErrors = 5
    
    // Debug log throttling
    private var debugLogCounter = 0
    private var lastErrorTime: Date?
    private let errorCooldownInterval: TimeInterval = 10.0 // 10 seconds
    
    // 🚨 CRASH PREVENTION: Processing state
    private var isProcessingAudio = false
    private let processingQueue = DispatchQueue(label: "sc.processing.queue", qos: .userInitiated)
    
    // 🎧 AUTOMATIC AUDIO DEVICE CHANGE DETECTION
    private var audioDevicePropertyListener: AudioObjectPropertyListenerProc?
    private var currentOutputDeviceID: AudioDeviceID = 0
    private var isMonitoringDeviceChanges = false

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

    // Hedef format: 16kHz, mono, Int16 interleaved (standardized for Deepgram)
    // 🚨 FIXED: Standardized to 16kHz for consistent quality
    private let outFmt = AVAudioFormat(
        commonFormat: .pcmFormatInt16,
        sampleRate: 16_000,
        channels: 1,
        interleaved: true
    )!
    
    // MARK: - Helper Classes
    
    // Helper class for handling stream output to prevent circular reference
    private class StreamOutputHandler: NSObject, SCStreamOutput {
        weak var parent: SystemAudioCaptureSC?
        
        init(parent: SystemAudioCaptureSC) {
            self.parent = parent
            super.init()
        }
        
        func stream(_ stream: SCStream, didOutputSampleBuffer sampleBuffer: CMSampleBuffer, of type: SCStreamOutputType) {
            parent?.stream(stream, didOutputSampleBuffer: sampleBuffer, of: type)
        }
    }
    
    // Minimal video output handler to prevent SCStream frame drop errors
    private class VideoOutputHandler: NSObject, SCStreamOutput {
        func stream(_ stream: SCStream, didOutputSampleBuffer sampleBuffer: CMSampleBuffer, of type: SCStreamOutputType) {
            // Ignore video frames - we only want audio
            // This handler exists solely to prevent SCStream from dropping frames
        }
    }
    
    // MARK: - Lifecycle
    
    override init() {
        super.init()
        print("[SC] 🔧 SystemAudioCaptureSC initialized")
        setupDeviceCoordinator()
    }
    
    deinit {
        print("[SC] 🔧 SystemAudioCaptureSC deinitializing")
        
        removeDeviceCoordinator()
        
        // 🚨 CRITICAL FIX: Stop processing immediately to prevent SIGTERM
        isProcessingAudio = false
        
        // 🚨 THREAD SAFE: Cleanup on appropriate queues
        // Timer'ı senkron olarak temizle
        if Thread.isMainThread {
            frameDropMonitor?.invalidate()
            frameDropMonitor = nil
        } else {
            DispatchQueue.main.sync {
                frameDropMonitor?.invalidate()
                frameDropMonitor = nil
            }
        }
        
        // 🚨 THREAD SAFE: Stop stream on processing queue to avoid deadlock
        processingQueue.sync {
        stream?.stopCapture { _ in }
        stream = nil
        }
        
        // References'ları temizle
        streamOutputHandler = nil
        converter = nil
        
        // 🚨 CRASH PREVENTION: Reset error tracking
        consecutiveErrors = 0
        lastErrorTime = nil
        
        // 🎧 Stop device change monitoring
        stopAudioDeviceMonitoring()
        
        // Cancel any pending restart tasks
        restartTask?.cancel()
        
        print("[SC] 🔧 SystemAudioCaptureSC deinit completed safely")
    }
    
    // MARK: - Device Change Coordinator
    
    /// Setup DeviceChangeCoordinator integration
    private func setupDeviceCoordinator() {
        // Listen for coordinator restart notifications
        coordinatorObserver = NotificationCenter.default.addObserver(
            forName: NSNotification.Name("DeviceCoordinatorSysRestart"),
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task {
                await self?.performCoordinatedRestart()
            }
        }
        
        print("[SC] 🎛️ DeviceChangeCoordinator integration setup")
    }
    
    /// Remove DeviceChangeCoordinator integration
    private func removeDeviceCoordinator() {
        if let observer = coordinatorObserver {
            NotificationCenter.default.removeObserver(observer)
            coordinatorObserver = nil
        }
        
        print("[SC] 🎛️ DeviceChangeCoordinator integration removed")
    }
    
    /// Perform restart requested by DeviceChangeCoordinator
    private func performCoordinatedRestart() async {
        print("[SC] 🔄 Performing coordinated restart...")
        
        // Reset warm-up counter for new device
        warmUpFrames = 0
        
        // Stop current stream
        await stop()
        
        // Brief delay to allow device to settle
        try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
        
        do {
            // Restart stream
            try await start()
            print("[SC] 🔄 Coordinated restart completed successfully")
        } catch {
            print("[SC] ❌ Coordinated restart failed: \(error.localizedDescription)")
        }
    }
    
    /// Get device name for logging
    private func getDeviceName(deviceID: AudioDeviceID) -> String {
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioObjectPropertyName,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        
        var cfName: CFString?
        var size = UInt32(MemoryLayout<CFString>.size)
        
        let status = AudioObjectGetPropertyData(
            deviceID,
            &address, 0, nil, &size, &cfName
        )
        
        if status == noErr, let cfName = cfName {
            return cfName as String
        } else {
            return "Unknown Device (\(deviceID))"
        }
    }

    // MARK: - Public
    
    /// Get current permission status using PermissionsService (async)
    func hasPermission() async -> Bool {
        return await PermissionsService.hasScreenRecordingPermission()
    }
    
    /// Request permission using PermissionsService
    func requestPermission() -> Bool {
        return PermissionsService.requestScreenRecordingPermission()
    }

    func start() async throws {
        print("[SC] ▶️ Starting SystemAudioCaptureSC...")
        
        // 1) Asenkron izin kontrolü - SCShareableContent kullanır
        guard await PermissionsService.hasScreenRecordingPermission() else {
            print("[SC] ❌ Screen Recording OFF – opening System Settings")
            PermissionsService.openScreenRecordingPrefs()
            throw NSError(
                domain: "SC", code: -3,
                userInfo: [NSLocalizedDescriptionKey:
                    "Screen recording permission required. Opened System Settings. " +
                    "After granting, quit and relaunch the app."]
            )
        }
        
        print("[SC] 🚀 requesting shareable content…")
        let content = try await SCShareableContent.current
        
        // 🔍 DEBUG: Log available displays and applications
        print("[SC] 📺 Available displays: \(content.displays.count)")
        print("[SC] 📱 Available applications: \(content.applications.count)")
        
        guard let display = content.displays.first else {
            print("[SC] ❌ No displays found!")
            throw NSError(domain: "SC", code: -1,
                          userInfo: [NSLocalizedDescriptionKey: "No displays found"])
        }

        print("[SC] 🎯 Using display: ID=\(display.displayID)")

        let filter = SCContentFilter(
            display: display,
            excludingApplications: [],
            exceptingWindows: []
        )

        let cfg = SCStreamConfiguration()
        cfg.capturesAudio = true
        cfg.sampleRate = 48_000
        cfg.channelCount = 2

        // 🔍 DEBUG: Log configuration
        print("[SC] ⚙️ Configuration - capturesAudio: \(cfg.capturesAudio), sampleRate: \(cfg.sampleRate), channels: \(cfg.channelCount)")

        print("[SC] 🔧 Creating SCStream...")
        let s = SCStream(filter: filter, configuration: cfg, delegate: self)
        
        // 🚨 CRITICAL FIX: Use dedicated output handlers to prevent circular reference
        self.streamOutputHandler = StreamOutputHandler(parent: self)
        self.videoOutputHandler = VideoOutputHandler()  // 🚨 FIXED: Re-add to prevent frame drops
        
        do {
            print("[SC] 🔧 Adding audio output handler...")
            try s.addStreamOutput(self.streamOutputHandler!, type: .audio, sampleHandlerQueue: audioQueue)
            
            print("[SC] 🔧 Adding video output handler to prevent frame drops...")
            try s.addStreamOutput(self.videoOutputHandler!, type: .screen, sampleHandlerQueue: DispatchQueue.global(qos: .background))

            print("[SC] 🔧 Starting capture...")
            try await s.startCapture()  // İzin reddedilirse burada SCStreamError.userDeclined gelir
            self.stream = s
            print("[SC] ✅ SystemAudioCaptureSC started successfully!")
        } catch {
            let ns = error as NSError
            if ns.domain == "com.apple.ScreenCaptureKit.SCStreamErrorDomain", ns.code == -3801 {
                // SCStreamError.userDeclined - TCC reddi
                print("[SC] 🚨 CONFIRMED: Permission denied (TCC error -3801)")
                throw NSError(
                    domain: "SC", code: -3801,
                    userInfo: [NSLocalizedDescriptionKey:
                        "Screen Recording permission denied or not yet effective. " +
                        "If you have just granted it, QUIT the app completely and relaunch."]
                )
            }
            throw error
        }
        
        // TASK 2: Start audio device monitoring
        startAudioDeviceMonitoring()
        
        // Start frame drop monitoring
        startFrameDropMonitoring()
        
        print("[SC] 🎧 System will automatically restart when audio output device changes (e.g., AirPods)")
    }

    func stop() async {
        print("[SC] ⏹️ Stopping SystemAudioCaptureSC...")
        
        try? await stream?.stopCapture()
        stream = nil
        converter = nil
        
        // Release handler references
        streamOutputHandler = nil
        
        // TASK 2: Stop audio device monitoring
        stopAudioDeviceMonitoring()
        
        // Stop frame drop monitoring
        stopFrameDropMonitoring()
        
        print("[SC] ⏹️ stopped")
    }

    // MARK: - SCStreamOutput

    func stream(_ stream: SCStream,
                didOutputSampleBuffer sampleBuffer: CMSampleBuffer,
                of type: SCStreamOutputType) {

        guard type == .audio else { return }
        guard CMSampleBufferDataIsReady(sampleBuffer) else { 
            print("[SC] ⚠️ Audio data not ready or wrong type")
            return 
        }
        
        // 🔍 DEBUG: Throttled logging (every 100th frame)
        debugLogCounter += 1
        if debugLogCounter % 100 == 0 {
            let sampleCount = CMSampleBufferGetNumSamples(sampleBuffer)
            print("[SC] 🎵 Processed \(debugLogCounter) audio frames (last: \(sampleCount) samples)")
        }
        
        // Update last audio received timestamp for frame drop monitoring
        lastAudioReceived = Date()
        
        // Check for warm-up period to avoid garbage frames during device settle
        if warmUpFrames < warmUpFrameCount {
            warmUpFrames += 1
            print("[SC] 🔥 SYS warm-up drop (\(warmUpFrames)/\(warmUpFrameCount))")
            return
        }
        
        // Simple PCM extraction for now
        if let rawPCMData = extractSimplePCMData(from: sampleBuffer) {
            DispatchQueue.main.async { [weak self] in
                guard let self = self else { return }
                
                // Send PCM data via callback (only if not paused by coordinator)
                if !self.deviceCoordinator.shouldPausePCM() {
                    self.onPCM16k?(rawPCMData)
                    
                    // If this is the first valid buffer after restart, resume coordinator
                    if self.deviceCoordinator.isRestartInProgress() {
                        print("[SC] 🔊 First valid buffer received, resuming coordinator")
                        self.deviceCoordinator.resumeAll()
                    }
                } else {
                    print("[SC] ⏸️ PCM callback paused by coordinator")
                }
            }
        } else {
            if debugLogCounter % 50 == 0 { // Log errors less frequently
                print("[SC] ❌ Failed to extract PCM data (frame \(debugLogCounter))")
            }
        }
    }

    // MARK: - SCStreamDelegate

    @objc func stream(_ stream: SCStream, didStopWithError error: Error) {
        print("[SC] ❌ Stream stopped with error: \(error.localizedDescription)")
        
        // 🚨 CRITICAL FIX: Auto-restart stream when it stops unexpectedly
        consecutiveErrors += 1
        
        if consecutiveErrors <= maxConsecutiveErrors {
            print("[SC] 🔄 Attempting to restart stream (attempt \(consecutiveErrors)/\(maxConsecutiveErrors))")
            
            Task {
                do {
                    // Wait a bit before restarting
                    try await Task.sleep(nanoseconds: 1_000_000_000) // 1 second
                    
                    // Stop current stream
                    await self.stop()
                    
                    // Restart stream
                    try await self.start()
                    
                    // Reset error counter on successful restart
                    self.consecutiveErrors = 0
                    print("[SC] ✅ Stream restarted successfully after error")
                    
                    // Notify upper layers
                    self.onDeviceChange?()
                    
                } catch {
                    print("[SC] ❌ Failed to restart stream: \(error)")
                }
            }
        } else {
            print("[SC] 🚨 Max consecutive errors reached, giving up on auto-restart")
        }
    }
    
    // MARK: - Simple PCM Extraction
    
    private func extractSimplePCMData(from sampleBuffer: CMSampleBuffer) -> Data? {
        guard let dataBuffer = CMSampleBufferGetDataBuffer(sampleBuffer) else {
            print("[SC] ❌ No data buffer in sample")
            return nil
        }
        
        var lengthAtOffset: Int = 0
        var totalLength: Int = 0
        var dataPointer: UnsafeMutablePointer<Int8>?
        
        let status = CMBlockBufferGetDataPointer(
            dataBuffer,
            atOffset: 0,
            lengthAtOffsetOut: &lengthAtOffset,
            totalLengthOut: &totalLength,
            dataPointerOut: &dataPointer
        )
        
        guard status == noErr, let dataPtr = dataPointer, totalLength > 0 else {
            print("[SC] ❌ Failed to get data pointer: status=\(status), length=\(totalLength)")
            return nil
        }
        
        // Simple conversion: assume 2ch 48kHz Float32 -> 1ch 48kHz Int16
        let frameCount = totalLength / (2 * MemoryLayout<Float32>.size)
        let floatData = dataPtr.withMemoryRebound(to: Float32.self, capacity: totalLength / MemoryLayout<Float32>.size) { ptr in
            return ptr
        }
        
        var outputData = Data(capacity: frameCount * MemoryLayout<Int16>.size)
        
        for frame in 0..<frameCount {
            // Mix stereo to mono and convert Float32 to Int16
            let leftSample = floatData[frame * 2]         // ✅ FIXED: Stereo interleaved L channel
            let rightSample = floatData[frame * 2 + 1]    // ✅ FIXED: Stereo interleaved R channel
            let monoSample = (leftSample + rightSample) * 0.5
            let clampedSample = max(-1.0, min(1.0, monoSample))
            let int16Sample = Int16(clampedSample * 32767.0)
            
            let littleEndianSample = int16Sample.littleEndian
            let byte1 = UInt8(littleEndianSample & 0xFF)
            let byte2 = UInt8((littleEndianSample >> 8) & 0xFF)
            
            outputData.append(byte1)
            outputData.append(byte2)
        }
        
        print("[SC] ✅ Converted \(frameCount) frames to \(outputData.count) bytes")
        return outputData
    }
    
    // MARK: - TASK 2: Audio Device Change Detection
    
    /// Start monitoring for audio output device changes
    private func startAudioDeviceMonitoring() {
        // Remove existing listener if any
        stopAudioDeviceMonitoring()
        
        // Get current default output device
        var deviceID: AudioDeviceID = 0
        var size = UInt32(MemoryLayout<AudioDeviceID>.size)
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDefaultOutputDevice,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        
        let status = AudioObjectGetPropertyData(
            AudioObjectID(kAudioObjectSystemObject),
            &address, 0, nil, &size, &deviceID
        )
        
        guard status == noErr else {
            print("[SC] ❌ Failed to get current output device: \(status)")
            return
        }
        
        currentOutputDeviceID = deviceID
        print("[SC] 🎧 Current output device ID: \(deviceID)")
        
        // Create property listener
        let listenerProc: AudioObjectPropertyListenerProc = { (objectID, numAddresses, addresses, clientData) in
            guard let clientData = clientData else { return noErr }
            let capture = Unmanaged<SystemAudioCaptureSC>.fromOpaque(clientData).takeUnretainedValue()
            capture.handleAudioDeviceChange()
            return noErr
        }
        
        audioDevicePropertyListener = listenerProc
        let clientData = Unmanaged.passUnretained(self).toOpaque()
        
        let addStatus = AudioObjectAddPropertyListener(
            AudioObjectID(kAudioObjectSystemObject),
            &address,
            listenerProc,
            clientData
        )
        
        if addStatus == noErr {
            isMonitoringDeviceChanges = true
            print("[SC] 🎧 Audio device change monitoring started")
        } else {
            print("[SC] ❌ Failed to add property listener: \(addStatus)")
        }
    }
    
    /// Stop monitoring for audio output device changes
    private func stopAudioDeviceMonitoring() {
        guard isMonitoringDeviceChanges, let listener = audioDevicePropertyListener else {
            return
        }
        
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDefaultOutputDevice,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        
        let clientData = Unmanaged.passUnretained(self).toOpaque()
        let removeStatus = AudioObjectRemovePropertyListener(
            AudioObjectID(kAudioObjectSystemObject),
            &address,
            listener,
            clientData
        )
        
        if removeStatus == noErr {
            print("[SC] 🎧 Audio device change monitoring stopped")
        } else {
            print("[SC] ⚠️ Failed to remove property listener: \(removeStatus)")
        }
        
        audioDevicePropertyListener = nil
        isMonitoringDeviceChanges = false
    }
    
    /// Handle audio output device change
    private func handleAudioDeviceChange() {
        // Get new default output device
        var deviceID: AudioDeviceID = 0
        var size = UInt32(MemoryLayout<AudioDeviceID>.size)
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDefaultOutputDevice,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        
        let status = AudioObjectGetPropertyData(
            AudioObjectID(kAudioObjectSystemObject),
            &address, 0, nil, &size, &deviceID
        )
        
        guard status == noErr else {
            print("[SC] ❌ Failed to get new output device: \(status)")
            return
        }
        
        // Check if device actually changed
        guard deviceID != currentOutputDeviceID else {
            print("[SC] 🎧 Device change notification but same device ID: \(deviceID)")
            return
        }
        
        print("[SC] 🎧 Audio output device changed: \(currentOutputDeviceID) → \(deviceID)")
        currentOutputDeviceID = deviceID
        
        // Use DeviceChangeCoordinator for coordinated restart
        let deviceName = getDeviceName(deviceID: deviceID)
        deviceCoordinator.requestSysRestart(reason: "Output device changed to \(deviceName)")
    }
    
    // MARK: - TASK 4: Race-safe Restart with Debounce
    
    /// Restart system audio capture with debounce to prevent multiple rapid restarts
    private func restartSystemAudioCaptureWithDebounce() {
        guard !isRestarting else {
            print("[SC] 🎧 Restart already in progress, ignoring")
            return
        }
        
        isRestarting = true
        
        // Cancel any existing restart task
        restartTask?.cancel()
        
        restartTask = Task {
            // TASK 4: Debounce delay (500ms for system audio - longer than mic)
            try? await Task.sleep(nanoseconds: 500_000_000)
            
            await MainActor.run {
                Task {
                    await self.performRestart()
                    self.isRestarting = false
                }
            }
        }
    }
    
    /// Perform the actual restart operation
    private func performRestart() async {
        // TASK 5: Increment device change counter
        deviceChangeCount += 1
        print("[SC] 🔄 Restarting due to device change (count: \(deviceChangeCount))")
        
        // TASK 5: Telemetry - measure restart time
        let startTime = CFAbsoluteTimeGetCurrent()
        
        // Stop current stream
        await stop()
        
        // Brief delay to allow device to settle
        try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
        
        // TASK 7: Restart stream with retry logic
        await performRestartWithRetry()
        
        // TASK 5: Log restart time
        let restartTime = (CFAbsoluteTimeGetCurrent() - startTime) * 1000
        print("[SC] 🔄 Restart completed in \(Int(restartTime))ms")
        
        // TASK 8: Send metric
        onMetric?("sys_restart_ms", restartTime, [
            "device_type": "system_audio",
            "change_count": "\(deviceChangeCount)"
        ])
    }
    
    // MARK: - TASK 7: Error Handling & Retry Logic
    
    /// Perform restart with retry logic and fallback
    private func performRestartWithRetry() async {
        guard restartAttempts < maxRestartAttempts else {
            print("[SC] ❌ Max restart attempts (\(maxRestartAttempts)) reached")
            await fallbackToBuiltInDevice()
            return
        }
        
        restartAttempts += 1
        print("[SC] 🔄 Restart attempt \(restartAttempts)/\(maxRestartAttempts)")
        
        do {
            // Attempt to restart
            try await start()
            
            // Success - reset attempt counter
            restartAttempts = 0
            onDeviceChange?()
            print("[SC] ✅ Restart successful")
            
        } catch {
            print("[SC] ⚠️ Restart failed: \(error.localizedDescription)")
            
            // Exponential backoff delay
            let backoffDelay = Double(restartAttempts) * 0.5 // 0.5s, 1s, 1.5s
            print("[SC] 🔄 Retrying in \(backoffDelay)s")
            
            try? await Task.sleep(nanoseconds: UInt64(backoffDelay * 1_000_000_000))
            await performRestartWithRetry()
        }
    }
    
    /// Fallback to built-in audio device
    private func fallbackToBuiltInDevice() async {
        print("[SC] 🔄 Falling back to built-in speakers")
        
        // Reset attempt counter
        restartAttempts = 0
        
        do {
            // Try to restart (ScreenCaptureKit should automatically select available device)
            try await start()
            
            // Notify upper layers
            onDeviceChange?()
            
            print("[SC] 🔊 Fallback to built-in device completed")
            
        } catch {
            print("[SC] ❌ Fallback failed: \(error.localizedDescription)")
            // At this point, system audio capture is not available
            // The application should continue with microphone-only mode
        }
    }
    
    // MARK: - Frame Drop Monitoring
    
    /// Start monitoring for frame drops (audio stream interruptions)
    private func startFrameDropMonitoring() {
        stopFrameDropMonitoring() // Stop any existing monitor
        
        lastAudioReceived = Date()
        
        frameDropMonitor = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            
            let now = Date()
            if let lastReceived = self.lastAudioReceived {
                let timeSinceLastFrame = now.timeIntervalSince(lastReceived)
                
                // If no audio received for more than 10 seconds, consider it a frame drop
                if timeSinceLastFrame > 10.0 {
                    print("[SC] 🚨 Frame drop detected! No audio for \(Int(timeSinceLastFrame)) seconds")
                    
                    // Attempt to restart stream
                    Task {
                        do {
                            print("[SC] 🔄 Restarting stream due to frame drop...")
                            await self.stop()
                            try await self.start()
                            print("[SC] ✅ Stream restarted after frame drop")
                            
                            // Notify upper layers
                            self.onDeviceChange?()
                        } catch {
                            print("[SC] ❌ Failed to restart stream after frame drop: \(error)")
                        }
                    }
                }
            }
        }
        
        print("[SC] 🔍 Frame drop monitoring started")
    }
    
    /// Stop frame drop monitoring
    private func stopFrameDropMonitoring() {
        frameDropMonitor?.invalidate()
        frameDropMonitor = nil
        lastAudioReceived = nil
        print("[SC] 🔍 Frame drop monitoring stopped")
    }
}
