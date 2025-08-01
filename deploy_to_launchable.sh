#!/bin/bash

# 🚀 NVIDIA Navigation API - Launchable Deployment Script
# Run this script on your Launchable instance after connecting

echo "🚀 Starting NVIDIA Navigation API deployment on Launchable..."

# Step 1: Update system
echo "📦 Updating system packages..."
sudo apt-get update -y

# Step 2: Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Step 3: Set up environment variables
echo "🔑 Setting up environment variables..."
echo "Please enter your Google Maps API key:"
read -r GOOGLE_MAPS_API_KEY
echo "Please enter your NVIDIA API key:"
read -r NVIDIA_API_KEY

# Create .env file
cat > .env << EOF
GOOGLE_MAPS_API_KEY=$GOOGLE_MAPS_API_KEY
NVIDIA_API_KEY=$NVIDIA_API_KEY
EOF

echo "✅ Environment variables saved to .env file"

# Step 4: Export for current session
export GOOGLE_MAPS_API_KEY=$GOOGLE_MAPS_API_KEY
export NVIDIA_API_KEY=$NVIDIA_API_KEY

# Step 5: Test the API
echo "🧪 Testing API configuration..."
python3 -c "
from nvidia_agent import NVIDIAAgent
agent = NVIDIAAgent(mock_mode=True)
intent = agent.parse_intent('Test deployment on Launchable', 'test')
print('✅ API test successful - Intent:', intent.get('intent_type'))
"

echo "🎯 Ready to start server!"
echo "Run: python3 main.py"
echo ""
echo "📡 Don't forget to expose port 8000 in your Launchable dashboard:"
echo "   1. Go to 'Using Ports' section"
echo "   2. Enter '8000' in the port field" 
echo "   3. Click 'Expose Port'"
echo ""
echo "🔗 Your API will be available at:"
echo "   - Local: http://localhost:8000"
echo "   - Public: https://your-exposed-url.brevlab.com/api/route" 