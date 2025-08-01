import requests
import os
from dotenv import load_dotenv
from typing import Optional, Tuple, List, Dict

# Load environment variables from .env file
load_dotenv()

class PlacesTextSearchClient:
    """
    Client for the Google Places Text Search API, returning only the top 
    results, each with name, formatted_address, latitude, and longitude.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"  # :contentReference[oaicite:0]{index=0}

    def search(
        self,
        query: str,
        location: Optional[Tuple[float, float]] = None,
        radius: int = 5000,
        place_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Perform a text search for places, returning up to 1 results
        with name, address, lat, and lng.
        """
        params = {
            "query": query,
            "key": self.api_key
        }
        if location:
            params["location"] = f"{location[0]},{location[1]}"
            params["radius"] = radius
        if place_type:
            params["type"] = place_type

        response = requests.get(self.base_url, params=params)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])[:1]  # top 1 only :contentReference[oaicite:1]{index=1}

        enriched = []
        for place in results:
            geom = place.get("geometry", {}).get("location", {})
            enriched.append({
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "latitude": geom.get("lat"),       # geometry.location.lat :contentReference[oaicite:2]{index=2}
                "longitude": geom.get("lng")       # geometry.location.lng :contentReference[oaicite:3]{index=3}
            })

        return enriched


if __name__ == "__main__":
    # Get API key from environment variables
    API_KEY = os.getenv("GOOGLE_API_KEY")
    if not API_KEY:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")
    
    client = PlacesTextSearchClient(API_KEY)
    
    # Example 1: Simple query with no location bias
    results = client.search("arcade")
    # Access the first enriched result's name, address, and coordinates
    print(
        "Top Arcade Result:",
        results[0]["name"],        # place name
        "-", 
        results[0]["address"],     # human-readable address
        "(lat:", results[0]["latitude"],  # latitude field
        "lng:", results[0]["longitude"], ")"  # longitude field
    )

    # Example 2: Query biased to San Francisco coordinates
    sf_location = (37.7749, -122.4194)
    sushi_places = client.search(
        "sushi place",
        location=sf_location,
        radius=3000,
        place_type="restaurant"
    )
    # Iterate through up to three enriched results
    for place in sushi_places:
        print(
            place["name"],         # name of the place
            "-", 
            place["address"],      # formatted address
            f"({place['latitude']},{place['longitude']})"  # coordinates
        )
