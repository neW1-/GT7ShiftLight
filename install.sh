#!/bin/bash

# GT7 Hue Shift Light - Installation Script
# This script will install all dependencies and help you configure the shift light

echo "🏁 GT7 Hue Shift Light Installation"
echo "=================================="
echo ""

# Check Python version
python_version=$(python3 --version 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "❌ Python 3 is not installed. Please install Python 3.7+ first."
    exit 1
fi
echo "✅ Python found: $python_version"

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip3 install --user -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies. Trying with --break-system-packages..."
    pip3 install --break-system-packages --user -r requirements.txt
fi

# Create config file if it doesn't exist
if [ ! -f "config.yaml" ]; then
    echo ""
    echo "📝 Creating configuration file..."
    cp config.yaml.example config.yaml
    echo "✅ Created config.yaml from example"
    echo ""
    echo "⚠️  IMPORTANT: Edit config.yaml with your settings:"
    echo "   - Home Assistant token and URL"
    echo "   - Hue light entity ID"  
    echo "   - PS5 IP address"
    echo ""
else
    echo "✅ Configuration file already exists"
fi

# Check if GT7 telemetry is enabled
echo "🎮 GT7 Setup Checklist:"
echo "   1. Enable telemetry in GT7: Settings → Network → Enable telemetry"
echo "   2. Note your PS5 IP: Settings → Network → View Connection Status"
echo ""

# Check Home Assistant setup
echo "🏠 Home Assistant Setup Checklist:"
echo "   1. Set up Philips Hue integration"
echo "   2. Create Long-Lived Access Token: Profile → Long-Lived Access Tokens"
echo "   3. Find light entity: Developer Tools → States → search for 'light.'"
echo ""

echo "✅ Installation complete!"
echo ""
echo "📖 Next steps:"
echo "   1. Edit config.yaml with your settings"
echo "   2. Run: python3 hueflash.py"
echo "   3. Start GT7 and test your shift light!"
echo ""
echo "🔗 For help, see README.MD or visit:"
echo "   https://github.com/RaceCrewAI/gt-telem"
