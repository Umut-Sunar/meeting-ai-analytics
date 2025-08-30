//
//  DeviceChangeCoordinator.swift
//  MacClient
//
//  Created by AI Assistant on 2025-08-30.
//  Copyright © 2025 Analytics System. All rights reserved.
//

import Foundation
import Dispatch

/// Coordinates device change restarts for MIC and SYS audio capture
/// Provides serialization, debouncing, and pause/resume functionality
class DeviceChangeCoordinator {
    
    // MARK: - Singleton
    
    static let shared = DeviceChangeCoordinator()
    
    private init() {
        setupCoordinator()
    }
    
    // MARK: - Properties
    
    /// Serial queue for coordinating device changes
    private let coordinatorQueue = DispatchQueue(label: "com.analytics.device-coordinator", qos: .userInitiated)
    
    /// Debounce timer for device changes
    private var debounceTimer: DispatchSourceTimer?
    
    /// Flag to prevent overlapping restarts
    private var isRestarting = false
    
    /// Flag to indicate if PCM callbacks should be paused
    private var isPaused = false
    
    /// Debounce delay in milliseconds
    private let debounceDelayMs: UInt64 = 400
    
    /// Pending restart operations
    private var pendingMicRestart: RestartRequest?
    private var pendingSysRestart: RestartRequest?
    
    /// Completion handlers for restart operations
    private var restartCompletionHandlers: [() -> Void] = []
    
    // MARK: - Types
    
    private struct RestartRequest {
        let reason: String
        let timestamp: Date
        let completion: (() -> Void)?
        
        init(reason: String, completion: (() -> Void)? = nil) {
            self.reason = reason
            self.timestamp = Date()
            self.completion = completion
        }
    }
    
    // MARK: - Setup
    
    private func setupCoordinator() {
        print("[DeviceCoordinator] 🎛️ Initialized device change coordinator")
    }
    
    // MARK: - Public Interface
    
    /// Request microphone restart with debouncing
    /// - Parameters:
    ///   - reason: Reason for the restart (for logging)
    ///   - completion: Optional completion handler called when restart completes
    func requestMicRestart(reason: String, completion: (() -> Void)? = nil) {
        coordinatorQueue.async {
            print("[DeviceCoordinator] 🎤 Mic restart requested: \(reason)")
            
            self.pendingMicRestart = RestartRequest(reason: reason, completion: completion)
            self.scheduleDebounceRestart()
        }
    }
    
    /// Request system audio restart with debouncing
    /// - Parameters:
    ///   - reason: Reason for the restart (for logging)
    ///   - completion: Optional completion handler called when restart completes
    func requestSysRestart(reason: String, completion: (() -> Void)? = nil) {
        coordinatorQueue.async {
            print("[DeviceCoordinator] 🔊 System audio restart requested: \(reason)")
            
            self.pendingSysRestart = RestartRequest(reason: reason, completion: completion)
            self.scheduleDebounceRestart()
        }
    }
    
    /// Pause all PCM callbacks during device changes
    func pauseAll() {
        coordinatorQueue.async {
            if !self.isPaused {
                self.isPaused = true
                print("[DeviceCoordinator] ⏸️ PCM callbacks paused")
            }
        }
    }
    
    /// Resume all PCM callbacks after device changes complete
    func resumeAll() {
        coordinatorQueue.async {
            if self.isPaused {
                self.isPaused = false
                print("[DeviceCoordinator] ▶️ PCM callbacks resumed")
                
                // Call completion handlers
                let handlers = self.restartCompletionHandlers
                self.restartCompletionHandlers.removeAll()
                
                DispatchQueue.main.async {
                    handlers.forEach { $0() }
                }
            }
        }
    }
    
    /// Check if PCM callbacks should be paused
    /// - Returns: true if callbacks should be paused
    func shouldPausePCM() -> Bool {
        return coordinatorQueue.sync {
            return isPaused
        }
    }
    
    /// Check if a restart is currently in progress
    /// - Returns: true if restart is in progress
    func isRestartInProgress() -> Bool {
        return coordinatorQueue.sync {
            return isRestarting
        }
    }
    
    // MARK: - Private Implementation
    
    /// Schedule debounced restart operation
    private func scheduleDebounceRestart() {
        // Cancel existing timer
        debounceTimer?.cancel()
        
        // Create new timer
        debounceTimer = DispatchSource.makeTimerSource(queue: coordinatorQueue)
        debounceTimer?.schedule(deadline: .now() + .milliseconds(Int(debounceDelayMs)))
        
        debounceTimer?.setEventHandler { [weak self] in
            self?.executeRestarts()
        }
        
        debounceTimer?.resume()
        
        print("[DeviceCoordinator] ⏱️ Debounce timer scheduled (\(debounceDelayMs)ms)")
    }
    
    /// Execute pending restart operations
    private func executeRestarts() {
        guard !isRestarting else {
            print("[DeviceCoordinator] ⚠️ Restart already in progress, ignoring")
            return
        }
        
        // Check if we have any pending restarts
        let hasMicRestart = pendingMicRestart != nil
        let hasSysRestart = pendingSysRestart != nil
        
        guard hasMicRestart || hasSysRestart else {
            print("[DeviceCoordinator] ℹ️ No pending restarts")
            return
        }
        
        isRestarting = true
        pauseAll()
        
        print("[DeviceCoordinator] 🔄 Executing coordinated restart...")
        
        // Collect completion handlers
        if let micCompletion = pendingMicRestart?.completion {
            restartCompletionHandlers.append(micCompletion)
        }
        if let sysCompletion = pendingSysRestart?.completion {
            restartCompletionHandlers.append(sysCompletion)
        }
        
        // Execute restarts sequentially to avoid conflicts
        Task {
            await performCoordinatedRestart(
                micRequest: pendingMicRestart,
                sysRequest: pendingSysRestart
            )
            
            await MainActor.run {
                coordinatorQueue.async {
                    self.isRestarting = false
                    self.pendingMicRestart = nil
                    self.pendingSysRestart = nil
                    
                    print("[DeviceCoordinator] ✅ Coordinated restart completed")
                }
            }
        }
    }
    
    /// Perform coordinated restart of audio components
    private func performCoordinatedRestart(
        micRequest: RestartRequest?,
        sysRequest: RestartRequest?
    ) async {
        let startTime = CFAbsoluteTimeGetCurrent()
        
        // Log restart details
        if let micRequest = micRequest {
            print("[DeviceCoordinator] 🎤 Restarting mic: \(micRequest.reason)")
        }
        if let sysRequest = sysRequest {
            print("[DeviceCoordinator] 🔊 Restarting system audio: \(sysRequest.reason)")
        }
        
        // Restart microphone first (typically faster)
        if micRequest != nil {
            await restartMicrophoneCapture()
        }
        
        // Then restart system audio
        if sysRequest != nil {
            await restartSystemAudioCapture()
        }
        
        // Brief delay to ensure both systems are stable
        try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
        
        let restartTime = (CFAbsoluteTimeGetCurrent() - startTime) * 1000
        print("[DeviceCoordinator] ⏱️ Total restart time: \(Int(restartTime))ms")
        
        // Resume will be called by the capture classes when they receive first valid buffer
    }
    
    /// Restart microphone capture
    private func restartMicrophoneCapture() async {
        await MainActor.run {
            // Notify MicCapture to perform restart
            NotificationCenter.default.post(
                name: NSNotification.Name("DeviceCoordinatorMicRestart"),
                object: nil
            )
        }
        
        // Wait for restart to complete
        try? await Task.sleep(nanoseconds: 200_000_000) // 200ms
    }
    
    /// Restart system audio capture
    private func restartSystemAudioCapture() async {
        await MainActor.run {
            // Notify SystemAudioCaptureSC to perform restart
            NotificationCenter.default.post(
                name: NSNotification.Name("DeviceCoordinatorSysRestart"),
                object: nil
            )
        }
        
        // Wait for restart to complete
        try? await Task.sleep(nanoseconds: 300_000_000) // 300ms
    }
    
    // MARK: - Cleanup
    
    deinit {
        debounceTimer?.cancel()
        print("[DeviceCoordinator] 🧹 Device coordinator deinitialized")
    }
}

// MARK: - Extensions

extension DeviceChangeCoordinator {
    
    /// Get current coordinator status for debugging
    func getStatus() -> [String: Any] {
        return coordinatorQueue.sync {
            return [
                "isRestarting": isRestarting,
                "isPaused": isPaused,
                "hasPendingMicRestart": pendingMicRestart != nil,
                "hasPendingSysRestart": pendingSysRestart != nil,
                "pendingCompletions": restartCompletionHandlers.count
            ]
        }
    }
    
    /// Force resume (for emergency situations)
    func forceResume() {
        coordinatorQueue.async {
            self.isPaused = false
            self.isRestarting = false
            self.pendingMicRestart = nil
            self.pendingSysRestart = nil
            self.restartCompletionHandlers.removeAll()
            
            print("[DeviceCoordinator] 🚨 Force resumed - all operations cleared")
        }
    }
}
