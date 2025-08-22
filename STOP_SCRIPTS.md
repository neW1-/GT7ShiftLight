## Ctrl+C Not Working? Here's How to Fix It

If you're having trouble stopping the GT7 Stream Deck script with Ctrl+C, here are several solutions:

### 🛑 **Quick Fix: Use the Kill Script**
```bash
./kill_gt7.sh
```

This will automatically find and terminate any running GT7 processes.

### ⌨️ **Manual Ctrl+C Tips**

1. **Try Ctrl+C multiple times** - Sometimes the first one doesn't register
2. **Try Ctrl+Z then kill** - This suspends the process:
   ```bash
   # Press Ctrl+Z to suspend
   jobs          # See job numbers
   kill %1       # Kill job 1 (adjust number as needed)
   ```

3. **Force quit in another terminal**:
   ```bash
   pkill -f streamdeck_gt7
   ```

### 🐛 **Why Ctrl+C Sometimes Doesn't Work**

The GT7 telemetry client runs in a separate thread and can block shutdown. This is common with:
- Network operations (UDP socket binding)
- Threading operations
- Home Assistant API calls

### 🔧 **Alternative Stop Methods**

1. **Close terminal window** - Forces all processes to stop
2. **Use Activity Monitor** - Find and quit the Python process
3. **Use process ID**:
   ```bash
   ps aux | grep streamdeck_gt7
   kill [PID_NUMBER]
   ```

### ✅ **Prevention Tips**

- **Don't run multiple instances** - Each script binds to the same UDP port
- **Wait for clean shutdown** - Give the script 2-3 seconds to cleanup
- **Check for stuck processes** before starting: `ps aux | grep gt7`

### 🚀 **Improved Scripts**

All scripts now have better shutdown handling:
- Multiple KeyboardInterrupt handlers  
- Shorter sleep intervals for faster response
- Better cleanup in signal handlers
- Automatic timeout detection

**Most reliable way to stop any GT7 script: Use the kill script!**
