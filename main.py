from flask import Flask, request, jsonify, render_template_string, send_from_directory
import logging
import traceback
import os
from starter import NVIDIAIntentParser
from scenic_agent import ScenicAgent
from fitness_agent import FitnessAgent
from fallback_agent import FallbackAgent
from polyline_agent import PolylineAgent

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='/static')
parser = NVIDIAIntentParser()

@app.route('/api/route', methods=['POST'])
def get_route():
    try:
        logger.info("Received POST request to /api/route")
        
        data = request.get_json()
        logger.info(f"Request data: {data}")
        
        prompt = data.get("prompt")
        user_ipv6 = data.get("ipv6", "2607:f140:6000:800e:384d:a5ee:7eb4:fa5e")  # fallback IPv6

        if not prompt:
            logger.error("Missing prompt in request")
            return jsonify({"error": "Missing prompt"}), 400

        logger.info(f"Processing prompt: {prompt}")
        
        # Parse prompt to RouteIntent
        logger.info("Parsing prompt to RouteIntent...")
        intent = parser.parse_prompt(prompt, user_ipv6)
        logger.info(f"Intent parsed: {intent.intent_type}")

        # Route to appropriate agent - Always return waypoints for iOS compatibility
        if intent.intent_type == "Scenic":
            logger.info("Using Scenic Agent")
            scenicAgent = ScenicAgent()
            resp = scenicAgent.get_scenic_route(intent)
        elif intent.intent_type == "Health":
            logger.info("Using Fitness Agent")
            fitnessAgent = FitnessAgent()
            resp = fitnessAgent.get_fitness_route(intent)
        else:
            # For Event, Commute, and Other intents, use Scenic Agent for waypoints format
            logger.info(f"Using Scenic Agent for {intent.intent_type} intent (waypoints format)")
            scenicAgent = ScenicAgent()
            resp = scenicAgent.get_scenic_route(intent)

        logger.info("Preparing response...")
        response = {
            "intent": intent.model_dump(),
            "waypoints": resp.model_dump()
        }
        
        logger.info("Response ready, sending to client")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in get_route: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy", "message": "MapsAI - NVIDIA Powered Navigation API is running"}), 200

@app.route('/', methods=['GET'])
def home():
    """Serve the main webapp interface"""
    try:
        file_path = os.path.join(app.static_folder, 'index.html')
        logger.info(f"Attempting to serve webapp from: {file_path}")
        with open(file_path, 'r') as f:
            content = f.read()
            logger.info("Successfully loaded webapp HTML")
            return content
    except FileNotFoundError as e:
        logger.error(f"Webapp file not found: {e}")
        return jsonify({
            "message": "🚀 Welcome to MapsAI - NVIDIA Powered Navigation API",
            "version": "2.0",
            "endpoints": {
                "/api/route": "POST - Get intelligent route recommendations",
                "/health": "GET - Health check"
            },
            "powered_by": "NVIDIA AI Models",
            "webapp": "Interactive chatbot interface not found. Please check static files."
        }), 200
    except Exception as e:
        logger.error(f"Error serving webapp: {e}")
        return jsonify({"error": "Unable to load webapp"}), 500

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory(app.static_folder, filename)

@app.route('/debug')
def debug():
    """Debug page for troubleshooting"""
    try:
        with open(os.path.join(app.static_folder, 'debug.html'), 'r') as f:
            return f.read()
    except FileNotFoundError:
        return jsonify({"error": "Debug page not found"}), 404

if __name__ == '__main__':
    logger.info("Starting Flask application on port 8000...")
    print("🚀 Starting MapsAI - NVIDIA Powered Navigation API on port 8000...")
    app.run(debug=False, host='127.0.0.1', port=8000)
