from typing import Dict, Optional, Literal, Any
from pydantic import BaseModel

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