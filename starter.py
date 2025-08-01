import re
import json
import requests
import os
from dotenv import load_dotenv
import google_text_search
from fitness_agent import FitnessAgent
from scenic_agent import ScenicAgent
from fallback_agent import FallbackAgent    
from polyline_agent import PolylineAgent
from models import LocationHint, RouteIntent
from typing import Dict, Optional, Literal, Any
from pydantic import BaseModel, validator
from nvidia_agent import NVIDIAAgent

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
if not NVIDIA_API_KEY:
    raise ValueError("NVIDIA_API_KEY environment variable is required. Set it with: export NVIDIA_API_KEY=your_key_here")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# --- Data Models (Structured Output) ---
class LocationHint(BaseModel):
    country: str
    region: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    coordinates: Optional[Dict[Literal["latitude", "longitude"], float]] = None

class RouteIntent(BaseModel):
    intent_type: Literal["Health", "Scenic", "Eco-conscious", "Commute", "Transit", "Event", "Road-Trip", "Other"]
    origin: str  # Address/coordinates
    destination: Optional[str] = None  # Address/coordinates (made optional)
    travel_modes: Optional[list[str]] = None  # Array of travel modes
    departure_time: Optional[str] = None  # ISO timestamp
    arrival_time: Optional[str] = None  # ISO timestamp
    constraints: list[str] = []
    avoid: Optional[list[str]] = None  # Route features to avoid
    optimize_waypoints: Optional[bool] = None  # Boolean for reordering stops
    stops: Optional[list[Dict[str, Any]]] = None  # For multi-stop routes with enriched data
    location_hint: Optional[LocationHint] = None  # User's inferred location

# --- Core NVIDIA Intent Parser ---
class NVIDIAIntentParser:
    def __init__(self):
        self.nvidia_agent = NVIDIAAgent(api_key=NVIDIA_API_KEY) 

    # TODO: This is a placeholder for the actual location hint extraction.
    def _extract_location_hint(self, ipv6: str) -> Optional[LocationHint]:
        """Extract approximate location from IPv6 (US-centric)."""
        try:
            # if ipv6.startswith("2607:f140"):  # Known US IPv6 prefix
            #     return LocationHint(country="US", region="East Coast")
          
            return LocationHint(
                country="US",
                region="California",
                city="San Francisco",
                postal_code=None,
                coordinates={
                    "latitude": 37.7749,
                    "longitude": -122.4194
                }
            )
        except:
            return None

    def _enrich_stops_with_google_search(self, route_intent: RouteIntent) -> RouteIntent:
        """Enrich each stop with Google Text Search results and return the modified RouteIntent."""
        if not route_intent.stops:
            return route_intent
            
        # Initialize Google Places client
        google_client = google_text_search.PlacesTextSearchClient(GOOGLE_API_KEY)
        
        # Get location coordinates for search bias
        location_coords = None
        if route_intent.location_hint and route_intent.location_hint.coordinates:
            location_coords = (route_intent.location_hint.coordinates["latitude"], route_intent.location_hint.coordinates["longitude"])
        
        enriched_stops = []
        for stop in route_intent.stops:
            # Create a copy of the stop to avoid modifying the original
            enriched_stop = stop.copy()
            
            # Search for the stop name or address
            search_query = stop.get("name") or stop.get("address") or "place"
            if search_query:
                try:
                    # Perform Google Text Search
                    search_results = google_client.search(
                        query=search_query,
                        location=location_coords,
                        radius=5000
                    )
                    
                    # Add search results to the stop
                    enriched_stop["gsr"] = search_results
                    
                except Exception as e:
                    # If search fails, add empty results but don't fail the entire process
                    enriched_stop["gsr"] = []
                    print(f"Warning: Google search failed for '{search_query}': {str(e)}")
            else:
                enriched_stop["gsr"] = []
            
            enriched_stops.append(enriched_stop)
        
        # Create a new RouteIntent with the enriched stops
        enriched_route_intent = RouteIntent(
            intent_type=route_intent.intent_type,
            origin=route_intent.origin,
            destination=route_intent.destination,
            travel_modes=route_intent.travel_modes,
            departure_time=route_intent.departure_time,
            arrival_time=route_intent.arrival_time,
            constraints=route_intent.constraints,
            avoid=route_intent.avoid,
            optimize_waypoints=route_intent.optimize_waypoints,
            stops=enriched_stops,
            location_hint=route_intent.location_hint
        )
        
        return enriched_route_intent

    def _parse_to_structured(self, prompt: str, ipv6: str) -> Dict:
        """Call NVIDIA's NLP model to extract intent."""
        return self.nvidia_agent.parse_intent(prompt, ipv6)

    def parse_prompt(self, prompt: str, user_ipv6: str) -> RouteIntent:
        """Main function: Parse natural language into a RouteIntent object."""
        # Step 1: Extract location hint for defaults
        location_hint = self._extract_location_hint(user_ipv6)
        
        # Step 2: Call ASI:One agent
        raw_response = self._parse_to_structured(prompt, user_ipv6)
        
        # Step 3: Validate and enrich response
        if not raw_response.get("destination"):
            if location_hint and location_hint.city:
                raw_response["destination"] = f"Nearby {location_hint.city}"
        
        # Step 4: Create RouteIntent object
        route_intent = RouteIntent(**raw_response, location_hint=location_hint)
        
        # Step 5: Enrich stops with Google search results if stops exist
        if route_intent.stops:
            enriched_route_intent = self._enrich_stops_with_google_search(route_intent)
            # Update the stops field with enriched data
            route_intent = enriched_route_intent
                
        return route_intent

# --- Example Usage ---
if __name__ == "__main__":
    # Example prompts matching your use cases
    # prompts = [
    #     "Give me a scenic route from UC Berkeley to Castro Valley",
    #     "Give me a route from UC Berkeley to Bushrod Park, I want to take 10000 steps",
    #     "Create a date night with stops at an arcade and sushi place"
    #     "I want to bike from UC Berkeley to Berkeley 2020 Oregon St, Berkeley, CA, but stop at at grocery store on the way"
    #     "I want a 10 000-step stroll starting and ending at 2601 Telegraph Ave, Berkeley."
    # ]
    
    # prompts = [
    #     "I want a 10 000-step stroll starting and ending at 2601 Telegraph Ave, Berkeley"
    # ]

    # hPrompts = [
    #     "I want a 10 000-step stroll starting and ending at 2601 Telegraph Ave, Berkeley",
    #     "I want to bike from UC Berkeley to 2020 Oregon St, Berkeley, CA, but stop at at grocery store on the way",
    #     "Give me a route from UC Berkeley to Bushrod Park, I want to take 10000 steps"
    # ]

    extraPrompts = [
        "Fastest morning commute from Oakland to downtown SF",
        "Build me a date-night route: first sushi, then an arcade, ending at a rooftop bar",
    ]

    parser = NVIDIAIntentParser()
    user_ipv6 = "2607:f140:6000:800e:384d:a5ee:7eb4:fa5e"  # From your context
    
    for prompt in extraPrompts:
        try:
            intent = parser.parse_prompt(prompt, user_ipv6)
            print(f"Prompt: '{prompt}'\nResult: {intent.model_dump_json(indent=2)}\n")

            if intent.intent_type == "Scenic":
                scenicAgent = ScenicAgent()
                resp = scenicAgent.get_scenic_route(intent)
            elif intent.intent_type == "Health":
                fitnessAgent = FitnessAgent()
                resp = fitnessAgent.get_fitness_route(intent)
            else:
                fallbackAgent = FallbackAgent()
                resp = fallbackAgent.get_waypoints(intent)

            print(resp.model_dump_json(indent=2))
            polylineAgent = PolylineAgent()
            resp = polylineAgent.get_route_summary(intent, resp.waypoints)
            print(resp)

        except Exception as e:
            print(f"Error parsing '{prompt}': {str(e)}")