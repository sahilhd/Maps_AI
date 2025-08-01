import os
from dotenv import load_dotenv
from typing import List, Dict
import googlemaps
from pydantic import BaseModel, Field
from models import RouteIntent

# Load environment variables from .env file
load_dotenv()

class RouteSummaryResponse(BaseModel):
    polyline: str = Field(..., description="Encoded overview polyline for the full route")
    total_distance_m: int = Field(..., description="Sum of all legs' distance in meters")
    total_duration_s: int = Field(..., description="Sum of all legs' duration in seconds")

class PolylineAgent:
    """
    Builds a driving route polyline through a list of lat/lng waypoints,
    and computes total distance & duration.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
        if not self.api_key:
            raise ValueError("Google Maps API key is required")
        self.client = googlemaps.Client(key=self.api_key)

    def get_route_summary(
        self,
        intent: RouteIntent,
        waypoints: List[Dict[str, float]],
        optimize: bool = False,
    ) -> RouteSummaryResponse:
        """
        Args:
           waypoints: Ordered list of {"lat": float, "lng": float}.  
                      Must have at least two points (origin & destination).
           optimize:  If True, lets Google reorder intermediate stops for shortest drive.

        Returns:
           RouteSummaryResponse containing:
             - polyline: overview encoded polyline
             - total_distance_m: sum of all legs (meters)
             - total_duration_s: sum of all legs (seconds)
        """
        if len(waypoints) < 2:
            raise ValueError("At least two waypoints (origin & destination) are required")

        # Format origin, destination, and intermediates as "lat,lng" strings
        origin = f"{waypoints[0]['lat']},{waypoints[0]['lng']}"
        destination = f"{waypoints[-1]['lat']},{waypoints[-1]['lng']}"
        intermediates = [f"{pt['lat']},{pt['lng']}" for pt in waypoints[1:-1]]

        # Build the pipe-delimited "avoid" string from the intent
        avoid_list = list(intent.avoid or [])
        if "ferries" not in avoid_list:
            avoid_list.append("ferries")
        avoid_param = "|".join(avoid_list) if avoid_list else None
        
        # Request Directions with driving mode
        directions_result = self.client.directions(
            origin=origin,
            destination=destination,
            mode=intent.travel_modes[0],
            waypoints=intermediates or None,
            optimize_waypoints=optimize,
            avoid=avoid_param,
        )
        if not directions_result:
            raise RuntimeError("No route returned by Directions API")

        route = directions_result[0]
        poly = route["overview_polyline"]["points"]

        total_distance = sum(leg["distance"]["value"] for leg in route["legs"])
        total_duration = sum(leg["duration"]["value"] for leg in route["legs"])

        return RouteSummaryResponse(
            polyline=poly,
            total_distance_m=total_distance,
            total_duration_s=total_duration
        )

# --- Usage Example ---

if __name__ == "__main__":
    # Replace with your Google Maps API key (or set the env var)
    API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
    agent = PolylineAgent(api_key=API_KEY)

    # A mock intent for testing purposes
    mock_intent = RouteIntent(
        intent_type="Scenic",
        origin="UC Berkeley",
        destination="Castro Valley",
        avoid=["tolls"]
    )
    
    # The provided waypoints:
    waypoints = [
        {"name": "UC Berkeley", "lat": 37.8712141, "lng": -122.255463},
        {"name": "Yogurt Park", "lat": 37.8678521, "lng": -122.2597825},
        {"name": "Willard Park", "lat": 37.8610841, "lng": -122.2566194},
        {"name": "Garber Park", "lat": 37.8621779, "lng": -122.2363179},
        {"name": "Temescal Regional Recreation Area", "lat": 37.8478593, "lng": -122.233447},
        {"name": "Montclair Park", "lat": 37.828797, "lng": -122.21199},
        {"name": "Castro Valley", "lat": 37.6955029, "lng": -122.0738678},
    ]

    # Strip out the "name" keys for the agent call
    coords_only = [{"lat": wp["lat"], "lng": wp["lng"]} for wp in waypoints]

    # Get the route summary
    summary = agent.get_route_summary(mock_intent, coords_only, optimize=False)

    print("Encoded Polyline:", summary.polyline)
    print(f"Total Distance: {summary.total_distance_m/1000:.2f} km")
    print(f"Total Duration: {summary.total_duration_s//60} min {summary.total_duration_s%60} sec")
    print("Avoided:", summary.avoid)
