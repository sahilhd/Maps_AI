import os
from dotenv import load_dotenv
import googlemaps
import polyline
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from models import RouteIntent  

# Load environment variables from .env file
load_dotenv()

class ScenicRouteResponse(BaseModel):
    waypoints: List[Dict[str, Any]]  # [{"name": ..., "lat": ..., "lng": ...}, …]

class ScenicAgent:
    """
    Computes an ordered list of scenic waypoints between origin, optional stops,
    and destination, respecting the user's travel mode and waypoint optimization preference.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
        if not self.api_key:
            raise ValueError("Missing Google Maps API key")
        self.client = googlemaps.Client(key=self.api_key)

    def get_scenic_route(self, intent: RouteIntent) -> ScenicRouteResponse:
        # Determine primary travel mode (default to driving)
        mode = intent.travel_modes[0] if intent.travel_modes else "driving"

        # 1. Build key points: origin → stops → destination
        points: List[Dict[str, Any]] = []

        # a) Origin
        orig = self._geocode(intent.origin)
        points.append({"name": intent.origin, "lat": orig["lat"], "lng": orig["lng"]})

        # b) Stops handling; if no destination and stops exist, last stop becomes destination
        stops = intent.stops[:] if intent.stops else []
        dest_point = None
        if (not intent.destination or not intent.destination.strip()) and stops:
            last = stops.pop()
            if last.get("gsr"):
                g = last["gsr"][0]
                dest_point = {"name": g.get("name", last["name"]), "lat": g["latitude"], "lng": g["longitude"]}
            else:
                addr = last.get("address") or last["name"]
                loc  = self._geocode(addr)
                dest_point = {"name": last["name"], "lat": loc["lat"], "lng": loc["lng"]}

        # c) Intermediate stops
        for stop in stops:
            if stop.get("gsr"):
                g = stop["gsr"][0]
                points.append({"name": g.get("name", stop["name"]), "lat": g["latitude"], "lng": g["longitude"]})
            else:
                addr = stop.get("address") or stop["name"]
                loc  = self._geocode(addr)
                points.append({"name": stop["name"], "lat": loc["lat"], "lng": loc["lng"]})

        # d) Destination
        if dest_point:
            points.append(dest_point)
        else:
            dest_str = intent.destination or (
                f"Nearby {intent.location_hint.city}"
                if intent.location_hint and intent.location_hint.city
                else intent.origin
            )
            loc = self._geocode(dest_str)
            points.append({"name": dest_str, "lat": loc["lat"], "lng": loc["lng"]})

        # 2. Build ordered waypoints: start with origin
        waypoints = [points[0]]

        # 3. For each leg, compute scenic segment and extract POI waypoints
        for start, end in zip(points, points[1:]):
            coords = self._best_scenic_segment(start, end, mode, bool(intent.optimize_waypoints))
            scenic_wpts = self._extract_scenic_waypoints(coords)
            waypoints.extend(scenic_wpts)
            waypoints.append(end)

        return ScenicRouteResponse(waypoints=waypoints)

    def _geocode(self, address: str) -> Dict[str, float]:
        res = self.client.geocode(address)
        if not res:
            raise RuntimeError(f"Geocode failed for '{address}'")
        return res[0]["geometry"]["location"]

    def _best_scenic_segment(
        self,
        start: Dict[str, float],
        end: Dict[str, float],
        mode: str,
        optimize: bool
    ) -> List[List[float]]:
        routes = self.client.directions(
            origin=(start["lat"], start["lng"]),
            destination=(end["lat"], end["lng"]),
            mode=mode,
            alternatives=True,
            optimize_waypoints=optimize
        )
        scored = []
        for r in routes:
            pts = polyline.decode(r["overview_polyline"]["points"])
            poi   = self._poi_density_score(pts)
            elev  = self._elevation_variation_score(pts)
            score = poi + 0.5 * elev
            scored.append((score, pts))
        return max(scored, key=lambda x: x[0])[1]

    def _poi_density_score(self, coords: List[List[float]]) -> float:
        interval = max(1, len(coords) // 10)
        total = 0
        for lat, lng in coords[::interval]:
            res = self.client.places_nearby(location=(lat, lng), radius=500, type="park")
            total += len(res.get("results", []))
        return total / max(1, len(coords) / 1000)

    def _elevation_variation_score(self, coords: List[List[float]]) -> float:
        samples = min(len(coords), 10)
        elev = self.client.elevation_along_path(path=coords, samples=samples)
        vals = [p["elevation"] for p in elev]
        return sum(abs(vals[i] - vals[i-1]) for i in range(1, len(vals)))

    def _extract_scenic_waypoints(self, coords: List[List[float]]) -> List[Dict[str, Any]]:
        interval = max(1, len(coords) // 10)
        seen = set()
        wpts: List[Dict[str, Any]] = []
        for lat, lng in coords[::interval]:
            results = self.client.places_nearby(
                location=(lat, lng),
                radius=500,
                keyword="park|viewpoint"
            ).get("results", [])
            if not results:
                continue
            top = results[0]
            pid = top["place_id"]
            if pid in seen:
                continue
            seen.add(pid)
            loc = top["geometry"]["location"]
            wpts.append({"name": top["name"], "lat": loc["lat"], "lng": loc["lng"]})
            if len(wpts) >= 5:
                break
        return wpts

# --- Usage Example ---
if __name__ == "__main__":
    intent = RouteIntent(
        intent_type="Scenic",
        origin="UC Berkeley",
        destination="Bushrod Park",
        travel_modes=["driving"],
        stops=[{
            "name": "Tilden Park",
            "address": "Tilden Regional Park, Berkeley, CA",
            "gsr": [{
                "name": "Tilden Park",
                "address": "Tilden Regional Park, Berkeley, CA",
                "latitude": 37.8840,
                "longitude": -122.2500
            }]
        }]
    )
    agent = ScenicAgent()
    resp = agent.get_scenic_route(intent)
    print(resp.model_dump_json(indent=2))
