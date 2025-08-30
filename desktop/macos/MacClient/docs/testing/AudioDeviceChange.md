# Audio Device Change Testing Guide

## 🎯 Overview

This document provides comprehensive testing procedures for the automatic audio device change detection and recovery system implemented in MacClient.

## 📋 Test Environment Setup

### Prerequisites
- macOS 13.0+ (for ScreenCaptureKit)
- Multiple audio devices available:
  - Built-in microphone and speakers
  - AirPods or Bluetooth headphones
  - USB headset or external microphone
  - USB DAC or external speakers
- MacClient application built and running
- Backend services running (WebSocket endpoints active)

### Test Data Collection
Monitor the following during tests:
- Application logs in MacClient UI
- Console.app logs for detailed debug output
- WebSocket connection stability
- Transcript continuity
- Performance metrics (restart times)

---

## 🧪 Test Scenarios

### **Scenario 1: Built-in Mic → AirPods (Microphone)**
**Objective**: Verify microphone device change detection and automatic restart

**Steps**:
1. Start MacClient with built-in microphone
2. Begin audio capture (start meeting)
3. Verify microphone audio is being captured and transmitted
4. Connect AirPods (pair if necessary)
5. Switch system audio input to AirPods in System Settings
6. Observe MacClient behavior

**Expected Results**:
- ✅ Device change detected within 100ms
- ✅ Audio capture automatically restarts within 500ms
- ✅ Total recovery time < 1 second
- ✅ WebSocket connection remains stable (no reconnection)
- ✅ Transcript flow continues without gaps
- ✅ UI shows device change notification: "🎧 Audio device changed — streams auto-restarted"
- ✅ Logs show: `[MIC] 🔄 Restarting due to device change (count: 1)`
- ✅ Metrics logged: `📊 Metric: mic_restart_ms=XXX [device_type=microphone, change_count=1]`

### **Scenario 2: AirPods → USB Headset (Microphone)**
**Objective**: Verify microphone change between external devices

**Steps**:
1. Start with AirPods as active microphone
2. Connect USB headset
3. Switch system audio input to USB headset
4. Observe automatic recovery

**Expected Results**:
- Same as Scenario 1, with `change_count=2`

### **Scenario 3: Built-in Speakers → AirPods (System Audio)**
**Objective**: Verify system audio output device change detection

**Steps**:
1. Start MacClient with built-in speakers as output
2. Begin system audio capture
3. Verify system audio is being captured
4. Connect AirPods
5. Switch system audio output to AirPods in System Settings
6. Play some system audio (music, video)
7. Observe MacClient behavior

**Expected Results**:
- ✅ Device change detected within 100ms
- ✅ System audio capture automatically restarts within 500ms
- ✅ Total recovery time < 1 second
- ✅ WebSocket connection remains stable
- ✅ System audio continues to be captured from new output device
- ✅ UI shows device change notification
- ✅ Logs show: `[SC] 🔄 Restarting due to device change (count: 1)`
- ✅ Metrics logged: `📊 Metric: sys_restart_ms=XXX [device_type=system_audio, change_count=1]`

### **Scenario 4: AirPods → USB DAC (System Audio)**
**Objective**: Verify system audio change between external devices

**Steps**:
1. Start with AirPods as active output
2. Connect USB DAC or external speakers
3. Switch system audio output to USB device
4. Verify system audio capture continues

**Expected Results**:
- Same as Scenario 3, with `change_count=2`

### **Scenario 5: Multiple Rapid Device Changes (Debounce Test)**
**Objective**: Verify debounce mechanism prevents multiple concurrent restarts

**Steps**:
1. Start MacClient with any audio devices
2. Rapidly switch between 3 different audio devices within 2 seconds:
   - Built-in → AirPods → USB → Built-in
3. Observe restart behavior

**Expected Results**:
- ✅ Only one restart operation occurs (debounce working)
- ✅ Logs show: "Restart already in progress, ignoring" for subsequent changes
- ✅ Final device change is properly detected after debounce period
- ✅ No race conditions or crashes
- ✅ CPU usage remains reasonable during rapid changes

### **Scenario 6: Device Removal During Recording**
**Objective**: Verify graceful handling of device disconnection

**Steps**:
1. Start recording with external device (AirPods or USB headset)
2. Physically disconnect/unpair the device during active recording
3. Observe fallback behavior

**Expected Results**:
- ✅ Device removal detected immediately
- ✅ Automatic fallback to built-in device within 1 second
- ✅ Recording continues with built-in device
- ✅ Logs show: `[MIC] 🔄 Falling back to built-in microphone`
- ✅ No crashes or audio stream interruption > 2 seconds

### **Scenario 7: All External Devices Disconnected**
**Objective**: Verify system behavior when only built-in devices available

**Steps**:
1. Start with external devices connected
2. Disconnect all external audio devices
3. Verify fallback to built-in devices

**Expected Results**:
- ✅ Graceful fallback to built-in microphone and speakers
- ✅ Continued operation with built-in devices
- ✅ Appropriate logging of fallback actions
- ✅ No system crashes or permanent audio loss

### **Scenario 8: WebSocket Stability During Device Changes**
**Objective**: Verify WebSocket connections remain stable during audio device changes

**Steps**:
1. Start MacClient and establish WebSocket connections
2. Monitor WebSocket connection status
3. Perform multiple device changes (Scenarios 1-4)
4. Verify WebSocket behavior

**Expected Results**:
- ✅ WebSocket connections never disconnect due to device changes
- ✅ PCM data flow resumes immediately after device restart
- ✅ No WebSocket reconnection attempts triggered
- ✅ Transcript WebSocket remains completely unaffected
- ✅ Backend continues receiving audio data without interruption

### **Scenario 9: System Sleep/Wake Cycle**
**Objective**: Verify device change detection works after system sleep

**Steps**:
1. Start MacClient with external devices
2. Put system to sleep for 30 seconds
3. Wake system
4. Change audio devices
5. Verify detection still works

**Expected Results**:
- ✅ Device change detection resumes after wake
- ✅ All restart mechanisms function normally
- ✅ No degraded performance after sleep/wake

### **Scenario 10: Long-running Stability Test**
**Objective**: Verify system stability over extended periods

**Steps**:
1. Start MacClient and begin recording
2. Perform device changes every 5 minutes for 30 minutes
3. Monitor memory usage, CPU usage, and system stability
4. Verify no memory leaks or performance degradation

**Expected Results**:
- ✅ Memory usage remains stable (< 5KB increase per change)
- ✅ CPU usage returns to baseline after each change
- ✅ No crashes or system instability
- ✅ All device changes continue to work correctly
- ✅ Performance metrics remain consistent

---

## 📊 Performance Benchmarks

### Target Metrics
- **Detection Latency**: < 100ms (framework notification speed)
- **Restart Latency**: < 500ms (audio engine restart)
- **Total Recovery Time**: < 1 second
- **WebSocket Stability**: 100% (no reconnections)
- **Memory Overhead**: < 5KB per audio source
- **CPU Impact**: < 1% steady state, 2-3% spike during transitions

### Measurement Tools
- Built-in telemetry: `📊 Metric: mic_restart_ms=XXX`
- System Activity Monitor for CPU/Memory
- Network tab in developer tools for WebSocket monitoring
- Console.app for detailed timing logs

---

## 🐛 Common Issues & Troubleshooting

### Issue: Device Changes Not Detected
**Symptoms**: No automatic restart when switching devices
**Possible Causes**:
- Audio session notifications not properly registered
- Core Audio property listener not active
- Device change happening too quickly (debounce interference)

**Debug Steps**:
1. Check logs for: `🎧 Audio route change notifications setup`
2. Check logs for: `🎧 Audio device change monitoring started`
3. Verify device actually changed in System Settings
4. Test with different device types

### Issue: Multiple Restarts for Single Change
**Symptoms**: Several restart attempts for one device change
**Possible Causes**:
- Debounce mechanism not working
- Multiple notification sources triggering simultaneously
- Race condition in restart logic

**Debug Steps**:
1. Check for: `Restart already in progress, ignoring`
2. Verify debounce delays (300ms mic, 500ms system)
3. Look for concurrent Task execution

### Issue: WebSocket Disconnection During Device Change
**Symptoms**: WebSocket reconnection attempts during audio restart
**Possible Causes**:
- Network layer interference (should not happen)
- Backend timeout during audio gap
- Client-side connection management issue

**Debug Steps**:
1. Monitor WebSocket connection logs
2. Check backend logs for connection drops
3. Verify PCM data flow timing

### Issue: Poor Performance During Device Changes
**Symptoms**: High CPU usage, slow restart times
**Possible Causes**:
- Inefficient restart logic
- Memory leaks in audio components
- Blocking operations on main thread

**Debug Steps**:
1. Profile with Instruments
2. Check memory usage trends
3. Verify async/await usage in restart logic

---

## ✅ Test Completion Checklist

### Core Functionality
- [ ] Microphone device changes detected and handled (Scenarios 1-2)
- [ ] System audio device changes detected and handled (Scenarios 3-4)
- [ ] Debounce mechanism prevents multiple restarts (Scenario 5)
- [ ] Device removal handled gracefully (Scenario 6)
- [ ] Fallback to built-in devices works (Scenario 7)

### Integration & Stability
- [ ] WebSocket connections remain stable (Scenario 8)
- [ ] System sleep/wake compatibility (Scenario 9)
- [ ] Long-running stability verified (Scenario 10)

### Performance
- [ ] Detection latency < 100ms
- [ ] Restart latency < 500ms
- [ ] Total recovery < 1 second
- [ ] Memory usage stable
- [ ] CPU impact minimal

### User Experience
- [ ] Clear status notifications in UI
- [ ] No manual intervention required
- [ ] Transcript continuity maintained
- [ ] No audio gaps > 1 second

### Error Handling
- [ ] Retry logic works for failed restarts
- [ ] Fallback mechanisms activate when needed
- [ ] No crashes under any test scenario
- [ ] Appropriate error logging

---

## 📝 Test Report Template

### Test Session Information
- **Date**: ___________
- **Tester**: ___________
- **MacClient Version**: ___________
- **macOS Version**: ___________
- **Hardware**: ___________

### Device Configuration
- **Built-in Audio**: ___________
- **External Device 1**: ___________
- **External Device 2**: ___________
- **External Device 3**: ___________

### Test Results Summary
- **Scenarios Passed**: ___/10
- **Performance Benchmarks Met**: ___/5
- **Critical Issues Found**: ___
- **Minor Issues Found**: ___

### Detailed Results
| Scenario | Status | Detection Time | Restart Time | Total Time | Notes |
|----------|--------|----------------|--------------|------------|-------|
| 1        | ✅/❌   | ___ms         | ___ms        | ___ms      | ___   |
| 2        | ✅/❌   | ___ms         | ___ms        | ___ms      | ___   |
| ...      | ...    | ...           | ...          | ...        | ...   |

### Issues Identified
1. **Issue**: ___________
   - **Severity**: Critical/Major/Minor
   - **Reproduction**: ___________
   - **Workaround**: ___________

### Recommendations
- [ ] Ready for production deployment
- [ ] Requires minor fixes before deployment
- [ ] Requires major fixes before deployment
- [ ] Additional testing needed in area: ___________

---

*Last Updated: 2025-01-29*  
*Version: 1.0*
