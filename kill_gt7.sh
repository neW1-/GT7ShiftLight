#!/bin/bash
# GT7 Process Killer
# Use this script to stop all GT7 telemetry processes if Ctrl+C doesn't work

echo "🔍 Looking for GT7 telemetry processes..."

# Find all GT7-related Python processes
GT7_PROCESSES=$(pgrep -f "(hueflash|drivetui|streamdeck_gt7|drive\.py)")

if [ -z "$GT7_PROCESSES" ]; then
    echo "✅ No GT7 telemetry processes found running"
    exit 0
fi

echo "Found GT7 processes:"
ps -p $GT7_PROCESSES -o pid,command

echo ""
echo "🛑 Sending SIGTERM to processes..."
kill -TERM $GT7_PROCESSES

# Wait a moment
sleep 2

# Check if any are still running
REMAINING=$(pgrep -f "(hueflash|drivetui|streamdeck_gt7|drive\.py)")

if [ -n "$REMAINING" ]; then
    echo "⚠️  Some processes still running, sending SIGKILL..."
    kill -KILL $REMAINING
    sleep 1
    
    # Final check
    FINAL_CHECK=$(pgrep -f "(hueflash|drivetui|streamdeck_gt7|drive\.py)")
    if [ -n "$FINAL_CHECK" ]; then
        echo "❌ Some processes couldn't be killed. You may need to restart your terminal."
    else
        echo "✅ All GT7 processes terminated"
    fi
else
    echo "✅ All GT7 processes terminated gracefully"
fi

echo ""
echo "💡 Tip: Next time try Ctrl+C first, then run this script if needed"
