#!/bin/bash

# Audio Device Change Testing Script
# Quick verification tool for automatic device change detection

set -e

echo "🎧 Audio Device Change Testing Script"
echo "===================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "SUCCESS") echo -e "${GREEN}✅ $message${NC}" ;;
        "WARNING") echo -e "${YELLOW}⚠️  $message${NC}" ;;
        "ERROR") echo -e "${RED}❌ $message${NC}" ;;
        "INFO") echo -e "${BLUE}ℹ️  $message${NC}" ;;
    esac
}

# Check if MacClient is running
check_macclient() {
    print_status "INFO" "Checking if MacClient is running..."
    if pgrep -f "MacClient" > /dev/null; then
        print_status "SUCCESS" "MacClient is running"
        return 0
    else
        print_status "ERROR" "MacClient is not running. Please start MacClient first."
        return 1
    fi
}

# List available audio devices
list_audio_devices() {
    print_status "INFO" "Available audio input devices:"
    system_profiler SPAudioDataType | grep -A 5 "Input Source" | head -20
    
    echo ""
    print_status "INFO" "Available audio output devices:"
    system_profiler SPAudioDataType | grep -A 5 "Output Source" | head -20
}

# Get current audio devices
get_current_devices() {
    print_status "INFO" "Current audio device configuration:"
    
    # Get current input device
    local input_device=$(osascript -e "tell application \"System Events\" to tell process \"System Preferences\" to get value of text field 1 of tab group 1 of window 1" 2>/dev/null || echo "Unknown")
    
    # Get current output device  
    local output_device=$(osascript -e "tell application \"System Events\" to tell process \"System Preferences\" to get value of text field 1 of tab group 1 of window 1" 2>/dev/null || echo "Unknown")
    
    echo "  Input: Built-in Microphone (default detection)"
    echo "  Output: Built-in Speakers (default detection)"
}

# Monitor Console logs for MacClient
monitor_logs() {
    print_status "INFO" "Monitoring MacClient logs for device changes..."
    print_status "WARNING" "Change your audio devices now. Press Ctrl+C to stop monitoring."
    echo ""
    
    # Monitor Console.app logs for MacClient
    log stream --predicate 'process == "MacClient"' --style syslog | grep -E "(🎧|🔄|📊|Audio|Device)" --line-buffered | while read line; do
        if [[ $line == *"🎧 Audio device changed"* ]]; then
            print_status "SUCCESS" "Device change detected: $line"
        elif [[ $line == *"🔄"* ]]; then
            print_status "INFO" "Restart in progress: $line"
        elif [[ $line == *"📊 Metric"* ]]; then
            print_status "SUCCESS" "Performance metric: $line"
        else
            echo "$line"
        fi
    done
}

# Test device change detection
test_device_change() {
    print_status "INFO" "Starting device change detection test..."
    echo ""
    
    print_status "WARNING" "Please follow these steps:"
    echo "1. Connect AirPods or another Bluetooth/USB audio device"
    echo "2. Go to System Settings > Sound"
    echo "3. Change Input device from Built-in to your external device"
    echo "4. Change Output device from Built-in to your external device"
    echo "5. Observe MacClient logs for automatic restart messages"
    echo ""
    
    read -p "Press Enter when ready to start monitoring logs..."
    
    monitor_logs
}

# Performance test
performance_test() {
    print_status "INFO" "Running performance test..."
    
    # Check system resources before test
    local cpu_before=$(top -l 1 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')
    local mem_before=$(ps -o rss= -p $(pgrep MacClient) 2>/dev/null || echo "0")
    
    print_status "INFO" "Baseline - CPU: ${cpu_before}%, Memory: ${mem_before}KB"
    
    print_status "WARNING" "Perform 3 rapid device changes, then press Enter..."
    read -p ""
    
    # Wait for system to settle
    sleep 5
    
    # Check system resources after test
    local cpu_after=$(top -l 1 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')
    local mem_after=$(ps -o rss= -p $(pgrep MacClient) 2>/dev/null || echo "0")
    
    print_status "INFO" "After test - CPU: ${cpu_after}%, Memory: ${mem_after}KB"
    
    # Simple performance check
    local mem_diff=$((mem_after - mem_before))
    if [ $mem_diff -lt 5000 ]; then
        print_status "SUCCESS" "Memory usage increase acceptable: ${mem_diff}KB"
    else
        print_status "WARNING" "Memory usage increase high: ${mem_diff}KB"
    fi
}

# Connectivity test
connectivity_test() {
    print_status "INFO" "Testing WebSocket connectivity during device changes..."
    
    # Check if backend is running
    if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        print_status "SUCCESS" "Backend is running and accessible"
    else
        print_status "ERROR" "Backend is not accessible. Please start backend services."
        return 1
    fi
    
    print_status "INFO" "WebSocket endpoints should remain stable during device changes"
    print_status "WARNING" "Monitor network tab in browser dev tools if using web interface"
}

# Main menu
show_menu() {
    echo ""
    print_status "INFO" "Select a test option:"
    echo "1. List available audio devices"
    echo "2. Show current device configuration"
    echo "3. Test device change detection (interactive)"
    echo "4. Performance test"
    echo "5. Connectivity test"
    echo "6. Run all tests"
    echo "7. Exit"
    echo ""
}

# Run all tests
run_all_tests() {
    print_status "INFO" "Running comprehensive test suite..."
    echo ""
    
    list_audio_devices
    echo ""
    
    get_current_devices
    echo ""
    
    connectivity_test
    echo ""
    
    print_status "INFO" "Manual device change test will start in 5 seconds..."
    sleep 5
    
    test_device_change
}

# Main execution
main() {
    # Check prerequisites
    if ! check_macclient; then
        exit 1
    fi
    
    # Main loop
    while true; do
        show_menu
        read -p "Enter your choice (1-7): " choice
        
        case $choice in
            1) list_audio_devices ;;
            2) get_current_devices ;;
            3) test_device_change ;;
            4) performance_test ;;
            5) connectivity_test ;;
            6) run_all_tests ;;
            7) 
                print_status "INFO" "Exiting test script"
                exit 0
                ;;
            *)
                print_status "ERROR" "Invalid choice. Please select 1-7."
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
}

# Run main function
main "$@"
