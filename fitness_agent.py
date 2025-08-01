# fitness_agent.py

import os
import re
import googlemaps
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from models import RouteIntent
from google_text_search import PlacesTextSearchClient
from nvidia_agent import NVIDIAAgent

# Load environment variables from .env file
load_dotenv()

class FitnessRouteMetrics(BaseModel):
    waypoints: List[Dict[str, Any]]
    total_distance_m: int
    total_duration_s: int
    calories_burned: float

class FitnessAgent:
    """
    - Builds point-to-point (origin→GSR stops→destination) or steps-loop (origin→POI→origin)
    - Estimates calories via MET × duration
    - Invokes ChatGPT for extra waypoints if constraints (steps/km/calories) are unmet
    """
    MET_VALUES = {"walking": 3.3, "bicycling": 6.0}
    DEFAULT_WEIGHT_KG = 70

    def __init__(self, maps_key: str = None, places_key: str = None, nvidia_key: str = None):
        self.gmaps = googlemaps.Client(key=maps_key or os.getenv("GOOGLE_MAPS_API_KEY"))
        self.places = PlacesTextSearchClient(places_key or os.getenv("GOOGLE_MAPS_API_KEY"))
        nvidia_api_key = nvidia_key or os.getenv("NVIDIA_API_KEY")
        if not nvidia_api_key:
            print("⚠️  WARNING: NVIDIA_API_KEY not found, using mock mode")
        self.nvidia = NVIDIAAgent(api_key=nvidia_api_key)

    def _geocode(self, addr: str) -> Dict[str, float]:
        res = self.gmaps.geocode(addr)
        if not res:
            raise RuntimeError(f"Geocode failed for '{addr}'")
        return res[0]["geometry"]["location"]

    def _estimate_calories(self, duration_s: int, mode: str, weight_kg: float) -> float:
        met = self.MET_VALUES.get(mode, self.MET_VALUES["walking"])
        mins = duration_s / 60
        return (met * 3.5 * weight_kg / 200) * mins

    def get_fitness_route(
        self,
        intent: RouteIntent,
        weight_kg: Optional[float] = None
    ) -> FitnessRouteMetrics:
        mode = (intent.travel_modes or ["walking"])[0].lower()
        if mode not in self.MET_VALUES:
            raise ValueError(f"Unsupported mode: {mode}")

        # 1) Parse constraints
        steps_m = None; target_m = None; target_cal = None
        for c in intent.constraints:
            if m := re.search(r"(\d+)\s*steps", c):
                steps_m = int(m.group(1)) * 0.8
            if m := re.search(r"(\d+(?:\.\d+)?)\s*km", c):
                target_m = float(m.group(1)) * 1000
            if m := re.search(r"burn\s*(\d+)\s*calorie", c):
                target_cal = float(m.group(1))

        # 2) Origin & destination
        origin = intent.origin
        dest   = intent.destination or origin

        # 3) Base route (steps-loop or point-to-point)
        if steps_m and origin == dest:
            loc = self._geocode(origin)
            poi = self.places.search(
                query="park|trail",
                location=(loc["lat"], loc["lng"]),
                radius=int(steps_m)
            )[0]
            wp = f"{poi['latitude']},{poi['longitude']}"
            directions = self.gmaps.directions(
                origin=(loc["lat"], loc["lng"]),
                destination=(loc["lat"], loc["lng"]),
                mode=mode,
                waypoints=[wp],
                optimize_waypoints=True
            )
        else:
            wp_coords = []
            if intent.stops:
                for stop in intent.stops:
                    if gsr := stop.get("gsr"):
                        g = gsr[0]
                        wp_coords.append(f"{g['latitude']},{g['longitude']}")
            start = self._geocode(origin)
            end   = self._geocode(dest)
            directions = self.gmaps.directions(
                origin=(start["lat"], start["lng"]),
                destination=(end["lat"], end["lng"]),
                mode=mode,
                waypoints=wp_coords or None,
                optimize_waypoints=bool(intent.optimize_waypoints)
            )

        if not directions:
            raise RuntimeError("No route found")
        route = directions[0]

        # 4) Totals
        total_dist = sum(leg["distance"]["value"] for leg in route["legs"])
        total_dur  = sum(leg["duration"]["value"] for leg in route["legs"])
        calories   = self._estimate_calories(total_dur, mode, weight_kg or self.DEFAULT_WEIGHT_KG)

        # 5) Build waypoints list
        out = []
        start_loc = route["legs"][0]["start_location"]
        out.append({"name": origin, "lat": start_loc["lat"], "lng": start_loc["lng"]})

        if steps_m and origin == dest:
            out.append({"name": poi["name"], "lat": poi["latitude"], "lng": poi["longitude"]})
            out.append({"name": origin, "lat": start_loc["lat"], "lng": start_loc["lng"]})
        else:
            if intent.stops:
                for stop in intent.stops:
                    if gsr := stop.get("gsr"):
                        g = gsr[0]
                        out.append({"name": g["name"], "lat": g["latitude"], "lng": g["longitude"]})
            end_loc = route["legs"][-1]["end_location"]
            out.append({"name": dest, "lat": end_loc["lat"], "lng": end_loc["lng"]})

        # 6) If constraints unmet, ask NVIDIA model for extras
        unmet = (
            (target_m   and total_dist < target_m) or
            (steps_m    and total_dist < steps_m) or
            (target_cal and calories < target_cal)
        )
        if unmet:
            current_metrics = {
                "distance_m": total_dist,
                "duration_s": total_dur,
                "calories": calories
            }
            extras = self.nvidia.optimize_fitness_route(
                current_route=out,
                constraints=intent.constraints,
                mode=mode,
                current_metrics=current_metrics
            )
            out.extend(extras)

        return FitnessRouteMetrics(
            waypoints=out,
            total_distance_m=total_dist,
            total_duration_s=total_dur,
            calories_burned=round(calories, 2)
        )

# Example Usage
if __name__ == "__main__":
    from models import RouteIntent
    import json

    raw = {
        "intent_type": "Health",
        "origin": "2601 Telegraph Ave, Berkeley",
        "destination": "2601 Telegraph Ave, Berkeley",
        "travel_modes": ["walking"],
        "constraints": ["10000 steps"],
        "avoid": None,
        "optimize_waypoints": None,
        "stops": None,
        "location_hint": None
    }
    intent = RouteIntent(**raw)
    agent = FitnessAgent()
    result = agent.get_fitness_route(intent)
    print(json.dumps(result.model_dump(), indent=2))
