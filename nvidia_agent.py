# nvidia_agent.py

import os
import json
import re
import requests
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

class NVIDIAAgent:
    """
    NVIDIA-based AI agent using NVIDIA's API for various route planning tasks.
    Supports different models for different use cases:
    - Intent parsing
    - Route planning
    - Fitness optimization
    - General chat
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.nvcf.nvidia.com/v1", mock_mode: bool = True):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        if not self.api_key and not mock_mode:
            raise ValueError("NVIDIA_API_KEY is required when not in mock mode. Set it with: export NVIDIA_API_KEY=your_key_here")
        self.base_url = base_url
        self.mock_mode = mock_mode  # Use mock responses for testing
        
    def _make_request(self, model_id: str, messages: List[Dict[str, str]], 
                     temperature: float = 0.7, max_tokens: int = 512) -> str:
        """
        Make a request to NVIDIA's API or return mock response
        """
        if self.mock_mode:
            return self._get_mock_response(messages)
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        # Use the correct NVIDIA API endpoint
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            params={"model": model_id}
        )
        
        if response.status_code != 200:
            # Try alternative endpoint format
            alt_response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            if alt_response.status_code != 200:
                raise RuntimeError(f"NVIDIA API error: {response.status_code} - {response.text}")
            response = alt_response
        
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()

    def _get_mock_response(self, messages: List[Dict[str, str]]) -> str:
        """Get dynamic mock responses based on user input for testing"""
        user_message = messages[-1]["content"] if messages else ""
        system_message = messages[0]["content"] if messages else ""
        
        # Intent parsing mock - parse actual user input
        if "Parse the user's request into JSON" in system_message or "intent_type" in system_message:
            # Extract intent from user message
            intent_type = "Other"
            origin = "UC Berkeley"  # default
            destination = ""
            travel_modes = ["driving"]
            constraints = []
            
            # Simple keyword detection for intent type
            if any(word in user_message.lower() for word in ["scenic", "beautiful", "nature", "park", "view"]):
                intent_type = "Scenic"
                constraints.append("scenic route")
            elif any(word in user_message.lower() for word in ["fitness", "walk", "exercise", "step", "steps", "calories", "health", "stroll", "jog", "run"]):
                intent_type = "Health"
                if any(word in user_message.lower() for word in ["step", "steps"]):
                    constraints.append("10000 steps")
                if "calories" in user_message.lower():
                    constraints.append("burn calories")
            elif any(word in user_message.lower() for word in ["date", "dinner", "night", "restaurant", "romantic"]):
                intent_type = "Event"
                constraints.append("date night")
            elif any(word in user_message.lower() for word in ["commute", "work", "fast", "quick", "shortest"]):
                intent_type = "Commute"
                constraints.append("fastest route")
            elif any(word in user_message.lower() for word in ["eco", "green", "environment", "electric"]):
                intent_type = "Eco-conscious"
                constraints.append("eco-friendly")
            
            # Extract locations using improved parsing
            if " from " in user_message.lower():
                parts = user_message.lower().split(" from ")
                if len(parts) > 1:
                    location_part = parts[1].split(" to ")[0].strip() if " to " in parts[1] else parts[1].strip()
                    origin = location_part.title()
            elif "starting at" in user_message.lower():
                parts = user_message.lower().split("starting at")
                if len(parts) > 1:
                    location_part = parts[1].split(",")[0].strip()  # Get address before comma
                    origin = location_part.title()
            elif " in " in user_message.lower():
                # Handle "walk in Toronto" or "route in downtown" patterns
                parts = user_message.lower().split(" in ")
                if len(parts) > 1:
                    location_part = parts[1].split()[0]  # Get first word after "in"
                    origin = location_part.title()
            
            if " to " in user_message.lower():
                parts = user_message.lower().split(" to ")
                if len(parts) > 1:
                    destination = parts[1].strip().title()
            
            # Extract travel modes
            if any(word in user_message.lower() for word in ["walk", "walking", "stroll", "step", "steps", "jog", "jogging"]):
                travel_modes = ["walking"]
            elif any(word in user_message.lower() for word in ["bike", "cycling", "bicycle"]):
                travel_modes = ["bicycling"]
            elif any(word in user_message.lower() for word in ["transit", "bus", "train"]):
                travel_modes = ["transit"]
            elif intent_type == "Health":  # Default to walking for health/fitness intents
                travel_modes = ["walking"]
            
            return f'''{{
                "intent_type": "{intent_type}",
                "origin": "{origin}",
                "destination": "{destination}",
                "travel_modes": {json.dumps(travel_modes)},
                "constraints": {json.dumps(constraints)},
                "avoid": [],
                "optimize_waypoints": true
            }}'''
        
        # Route planning mock - generate different waypoints based on intent
        elif "generate a JSON array of waypoints" in system_message or "Generate waypoints" in user_message:
            # Parse intent from user input to generate appropriate waypoints
            if any(word in user_message.lower() for word in ["scenic", "beautiful", "nature", "park"]):
                return '''[
                    {"name": "Starting Point", "lat": 37.8712141, "lng": -122.255463},
                    {"name": "Tilden Regional Park", "lat": 37.8840, "lng": -122.2500},
                    {"name": "Berkeley Hills Scenic Overlook", "lat": 37.8900, "lng": -122.2400},
                    {"name": "Destination", "lat": 37.6955029, "lng": -122.0738678}
                ]'''
            elif any(word in user_message.lower() for word in ["fitness", "health", "walk", "exercise", "step", "steps", "stroll", "jog", "run"]):
                return '''[
                    {"name": "Starting Point", "lat": 37.8712141, "lng": -122.255463},
                    {"name": "Berkeley Marina", "lat": 37.8600, "lng": -122.3200},
                    {"name": "Cesar Chavez Park", "lat": 37.8650, "lng": -122.3150},
                    {"name": "Fitness Loop Return", "lat": 37.8712141, "lng": -122.255463}
                ]'''
            elif any(word in user_message.lower() for word in ["date", "dinner", "romantic", "night"]):
                return '''[
                    {"name": "Starting Point", "lat": 37.8712141, "lng": -122.255463},
                    {"name": "Romantic Restaurant", "lat": 37.8720, "lng": -122.2682},
                    {"name": "Sunset Viewpoint", "lat": 37.8811, "lng": -122.2968},
                    {"name": "Evening Destination", "lat": 37.8750, "lng": -122.2590}
                ]'''
            elif any(word in user_message.lower() for word in ["commute", "work", "fast", "quick"]):
                return '''[
                    {"name": "Starting Point", "lat": 37.8712141, "lng": -122.255463},
                    {"name": "Highway Entrance", "lat": 37.8500, "lng": -122.2300},
                    {"name": "Express Route", "lat": 37.8000, "lng": -122.2000},
                    {"name": "Work Destination", "lat": 37.7500, "lng": -122.1500}
                ]'''
            else:
                return '''[
                    {"name": "Starting Point", "lat": 37.8712141, "lng": -122.255463},
                    {"name": "Intermediate Stop", "lat": 37.8000, "lng": -122.2000},
                    {"name": "Final Destination", "lat": 37.7500, "lng": -122.1500}
                ]'''
        
        # Fitness optimization mock
        elif "fitness route optimizer" in system_message or "fitness" in user_message:
            return '''[
                {"name": "Berkeley Marina Fitness Loop", "lat": 37.8600, "lng": -122.3200},
                {"name": "Cesar Chavez Park Track", "lat": 37.8650, "lng": -122.3150}
            ]'''
        
        # General chat mock
        else:
            return "I'm an NVIDIA AI assistant. I can help you plan routes based on your preferences. Try asking for a scenic route, fitness walk, or commute path!"

    def parse_intent(self, prompt: str, ipv6: str) -> Dict[str, Any]:
        """
        Parse natural language prompt into structured RouteIntent using NVIDIA's 
        best model for intent classification and structured output.
        """
        system_prompt = f"""
You are an intelligent route-planning assistant. Parse the user's request into JSON with:
- intent_type: one of: "Health", "Scenic", "Eco-conscious", "Commute", "Transit", "Event", "Road-Trip", "Other".
- origin: starting point ("UC Berkeley" if unspecified).
- destination: end point.
- travel_modes: array of one or more modes in preferred order, any of ["driving", "walking", "bicycling", "transit"]. Use "driving" if nothing mentioned.
- departure_time / arrival_time: optional ISO timestamps for routing with traffic or schedules.
- constraints: list of conditions (e.g. "avoid tolls", "burn 100 calories, "date night", "x km").
- avoid: list of route features to avoid (tolls, highways, ferries).
- stops: If the user mentions multiple stops, list them here as an array of dictionaries (e.g., [{{name: place}}]). If no stops, this can be omitted.
- optimize_waypoints: boolean (true to reorder stops for shortest trip).
User IP hint: {ipv6}.  
Respond ONLY with the raw JSON object, without any explanatory text or markdown formatting.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # Use NVIDIA's best model for structured output
        response = self._make_request(
            model_id="nvidia/llama3-8b-instruct",  # Good for structured output
            messages=messages,
            temperature=0.1,  # Low temperature for consistent JSON
            max_tokens=1000
        )
        
        # Extract JSON from response
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            json_string = match.group(0)
            return json.loads(json_string)
        
        raise ValueError("Could not find a valid JSON object in the NVIDIA model's response.")

    def plan_route(self, intent: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate route waypoints using NVIDIA's model optimized for route planning.
        """
        system_prompt = """
You are a route planner. Given route intent details, generate a JSON array of waypoints.
Each waypoint should have: {"name": "place name", "lat": latitude, "lng": longitude}
Return ONLY the JSON array, no explanation.
"""

        user_prompt = f"""
Intent: {intent.get('intent_type', 'Other')}
Origin: {intent.get('origin', '')}
Destination: {intent.get('destination', '')}
Travel modes: {intent.get('travel_modes', ['driving'])}
Constraints: {intent.get('constraints', [])}
Avoid: {intent.get('avoid', [])}
Stops: {intent.get('stops', [])}

Generate waypoints as JSON array: [{{"name": "...", "lat": ..., "lng": ...}}, ...]
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self._make_request(
            model_id="nvidia/llama3-8b-instruct",  # Good for structured planning
            messages=messages,
            temperature=0.2,
            max_tokens=500
        )
        
        # Extract JSON array
        start, end = response.find("["), response.rfind("]")
        if start == -1 or end == -1:
            raise RuntimeError("No JSON array found in NVIDIA model response")
        
        try:
            return json.loads(response[start:end+1])
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON from NVIDIA model: {e}")

    def optimize_fitness_route(self, current_route: List[Dict[str, Any]], 
                              constraints: List[str], mode: str, 
                              current_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Optimize fitness route using NVIDIA's model specialized for health/fitness planning.
        """
        system_prompt = """
You are a fitness route optimizer. Given current route metrics and fitness constraints,
suggest additional waypoints to meet fitness goals. Return only JSON array of waypoints.
"""

        user_prompt = f"""
Current route waypoints: {current_route}
Travel mode: {mode}
Current metrics: {current_metrics}
Fitness constraints: {constraints}

Suggest up to 3 extra waypoints as JSON array to satisfy fitness goals:
[{{"name": "place name", "lat": latitude, "lng": longitude}}, ...]
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self._make_request(
            model_id="nvidia/llama3-8b-instruct",  # Good for optimization tasks
            messages=messages,
            temperature=0.3,
            max_tokens=300
        )
        
        # Extract JSON array
        match = re.search(r'\[.*\]', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        
        return []  # Return empty if parsing fails

    def chat(self, prompt: str, temperature: float = 0.7, max_tokens: int = 512) -> str:
        """
        General chat interface using NVIDIA's conversational model.
        """
        messages = [
            {"role": "system", "content": "You are a helpful route planning assistant."},
            {"role": "user", "content": prompt}
        ]
        
        return self._make_request(
            model_id="nvidia/llama3-8b-instruct",  # Good for general conversation
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

# Example usage
if __name__ == "__main__":
    agent = NVIDIAAgent()
    
    # Test intent parsing
    intent = agent.parse_intent(
        "I want a scenic route from UC Berkeley to Castro Valley",
        "2607:f140:6000:800e:384d:a5ee:7eb4:fa5e"
    )
    print("Intent:", json.dumps(intent, indent=2))
    
    # Test route planning
    waypoints = agent.plan_route(intent)
    print("Waypoints:", json.dumps(waypoints, indent=2)) 