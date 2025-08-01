#!/bin/bash

# 🔐 MapsAI - Secure Setup Script
# This script helps you set up MapsAI with your own API keys

echo "🚀 MapsAI - NVIDIA Powered Navigation Assistant Setup"
echo "=================================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "⚡ Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "🔑 API Key Configuration"
echo "======================="
echo ""
echo "You need to provide your own API keys:"
echo "1. Google Maps API Key: https://console.cloud.google.com/"
echo "2. NVIDIA API Key: https://build.nvidia.com/"
echo ""

# Prompt for API keys
read -p "Enter your Google Maps API Key: " GOOGLE_MAPS_KEY
read -p "Enter your NVIDIA API Key: " NVIDIA_KEY

# Validate that keys were provided
if [ -z "$GOOGLE_MAPS_KEY" ] || [ -z "$NVIDIA_KEY" ]; then
    echo "❌ Error: Both API keys are required!"
    exit 1
fi

# Update the HTML file with the Google Maps key
echo "🔧 Configuring Google Maps integration..."
sed -i.bak "s/YOUR_GOOGLE_MAPS_API_KEY/$GOOGLE_MAPS_KEY/g" static/index.html

# Export environment variables
export GOOGLE_MAPS_API_KEY="$GOOGLE_MAPS_KEY"
export NVIDIA_API_KEY="$NVIDIA_KEY"

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "🚀 Starting MapsAI server..."
echo "   Webapp: http://localhost:8000/"
echo "   API: http://localhost:8000/api/route"
echo ""

# Start the server
python main.py 