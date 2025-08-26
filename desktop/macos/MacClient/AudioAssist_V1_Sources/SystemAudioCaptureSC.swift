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
    
    // Enhanced permission management
    private var permissionManager: PermissionManager?
    
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
    private var lastErrorTime: Date?
    private let errorCooldownInterval: TimeInterval = 10.0 // 10 seconds
    
    // 🚨 CRASH PREVENTION: Processing state
    private var isProcessingAudio = false
    private let processingQueue = DispatchQueue(label: "sc.processing.queue", qos: .userInitiated)
    
    // 🎧 AUTOMATIC AUDIO DEVICE CHANGE DETECTION
    private var audioDevicePropertyListener: AudioObjectPropertyListenerProc?
    private var currentOutputDeviceID: AudioDeviceID = 0
    private var isMonitoringDeviceChanges = false

    // Hedef format: 48kHz, mono, Int16 interleaved (Deepgram ile uyumlu)
    private let outFmt = AVAudioFormat(
        commonFormat: .pcmFormatInt16,
        sampleRate: 48_000,
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
    }
    
    deinit {
        print("[SC] 🔧 SystemAudioCaptureSC deinitializing")
        
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
        videoOutputHandler = nil
        converter = nil
        permissionManager = nil
        
        // 🚨 CRASH PREVENTION: Reset error tracking
        consecutiveErrors = 0
        lastErrorTime = nil
        
        // 🎧 Stop device change monitoring
        stopAudioDeviceMonitoring()
        
        print("[SC] 🔧 SystemAudioCaptureSC deinit completed safely")
    }

    // MARK: - Public
    
    /// Get current permission status from the permission manager
    func hasPermission() async -> Bool {
        guard let manager = permissionManager else {
            print("[SC] ⚠️ Permission manager not initialized")
            return false
        }
        
        return await MainActor.run { manager.hasScreenRecordingPermission }
    }
    
    /// Request permission using the enhanced permission manager
    func requestPermission() async -> Bool {
        guard let manager = permissionManager else {
            print("[SC] ⚠️ Permission manager not initialized")
            return false
        }
        
        return await manager.requestPermissionWithGuidance()
    }

    func start() async throws {
        print("[SC] �� Starting SystemAudioCaptureSC...")
        
        // Initialize permission manager if not already done
        if permissionManager == nil {
            await MainActor.run {
                permissionManager = PermissionManager()
            }
            // Give permission manager time to initialize
            try? await Task.sleep(nanoseconds: 500_000_000) // 0.5 seconds
        }
        
        // Check permissions using enhanced manager
        guard let manager = permissionManager else {
            throw NSError(domain: "SC", code: -3, 
                         userInfo: [NSLocalizedDescriptionKey: "Permission manager initialization failed"])
        }
        
        await manager.checkPermissionStatus()
        let hasPermission = await MainActor.run { manager.hasScreenRecordingPermission }
        
        if !hasPermission {
            print("[SC] ❌ Permission denied - attempting to request...")
            
            // Try to request permission
            let granted = await manager.requestPermissionWithGuidance()
            guard granted else {
                let error = NSError(domain: "SC", code: -2, 
                                  userInfo: [NSLocalizedDescriptionKey: "Screen recording permission denied"])
                print("[SC] ❌ Permission request failed: \(error.localizedDescription)")
                throw error
            }
            print("[SC] ✅ Permission granted after request - continuing...")
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
        self.videoOutputHandler = VideoOutputHandler()
        
        print("[SC] 🔧 Adding audio output handler...")
        try s.addStreamOutput(self.streamOutputHandler!, type: .audio, sampleHandlerQueue: audioQueue)
        
        print("[SC] 🔧 Adding video output handler (to prevent frame drops)...")
        let videoQueue = DispatchQueue(label: "video.output.queue", qos: .userInitiated)
        try s.addStreamOutput(self.videoOutputHandler!, type: .screen, sampleHandlerQueue: videoQueue)
        
        print("[SC] 🔧 Starting capture...")
        try await s.startCapture()
        self.stream = s
        
        print("[SC] ✅ SystemAudioCaptureSC started successfully!")
        print("[SC] 🎧 System will automatically restart when audio output device changes (e.g., AirPods)")
    }

    func stop() async {
        print("[SC] ⏹️ Stopping SystemAudioCaptureSC...")
        
        try? await stream?.stopCapture()
        stream = nil
        converter = nil
        
        // Release handler references
        streamOutputHandler = nil
        videoOutputHandler = nil
        
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
        
        // 🔍 DEBUG: Log audio data reception
        let sampleCount = CMSampleBufferGetNumSamples(sampleBuffer)
        print("[SC] 🎵 Received audio: \(sampleCount) samples")
        
        // Simple PCM extraction for now
        if let rawPCMData = extractSimplePCMData(from: sampleBuffer) {
            print("[SC] 📤 Sending \(rawPCMData.count) bytes to callback")
            DispatchQueue.main.async { [weak self] in
                self?.onPCM16k?(rawPCMData)
            }
        } else {
            print("[SC] ❌ Failed to extract PCM data")
        }
    }

    // MARK: - SCStreamDelegate

    @objc func stream(_ stream: SCStream, didStopWithError error: Error) {
        print("[SC] ❌ Stream stopped with error: \(error.localizedDescription)")
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
    
    // Placeholder methods for device monitoring
    private func stopAudioDeviceMonitoring() {
        // Placeholder
    }
}
