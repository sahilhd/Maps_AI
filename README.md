# MapsAI
![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)



A next-generation, AI-powered navigation app that transforms your natural language prompts into hyper-personalized routes. Whether you’re craving a scenic drive, a calorie-burning stroll, or a foodie adventure, Navi has you covered.

---

## 📋 Table of Contents
- [Inspiration](#inspiration)
- [Architecture Overview](#architecture-overview)
- [Agents](#agents)
  - [1. FetchAI Intent Parser](#1-fetchai-intent-parser)
  - [2. Scenic Agent](#2-scenic-agent)
  - [3. Polyline Agent](#3-polyline-agent)
  - [4. GPT Agent (`ChatGPTAgent`)](#4-gpt-agent-chatgptagent)
  - [5. Google Text Search Agent (`PlacesTextSearchClient`)](#5-google-text-search-agent-placestextsearchclient)
  - [6. Fitness Agent](#6-fitness-agent)
  - [7. Fallback Agent](#7-fallback-agent)
- [Getting Started](#getting-started)

---

## Inspiration
Traditional navigation apps focus solely on speed. But sometimes, you want more than just the fastest path:
- A sunrise walk along the coast 🌅
- A scenic drive through rolling hills 🏞️
- A 10,000-step fitness loop 🚶‍♀️
- A multi-stop foodie crawl 🍣🕹️🍹

Navi empowers you to route on your terms—by simply telling it what you want.

---

## Architecture Overview
At its core, Navi orchestrates multiple specialized AI agents alongside Google Maps APIs. A central intent parser routes your request to the right agent(s), which then compute and refine the perfect route.

---

## Agents

### 1. FetchAI Intent Parser
- **Role**: Converts free-form prompts into a structured `RouteIntent` schema.
- **Mechanism**: Uses ASI:One LLM (asi1-mini) to extract intent type, origin, destination, travel modes, constraints, stops, and location hints.
- **Purpose**: Normalizes messy user language for downstream agents.

### 2. Scenic Agent
- **Role**: Finds the most visually appealing route.
- **Mechanism**:
  - Retrieves alternative routes via Google Directions API.
  - Scores each by park density (`places_nearby`) and elevation variation (`elevation_along_path`).
  - Picks the top route and extracts scenic POI waypoints.
- **Purpose**: Delivers routes optimized for experience over speed.

### 3. Polyline Agent
- **Role**: Builds a continuous polyline and calculates total distance/duration.
- **Mechanism**:
  - Takes an ordered list of `{lat, lng}` waypoints.
  - Calls Google Directions API with waypoint optimization and avoid rules.
  - Summarizes the encoded `overview_polyline` and aggregates leg metrics.
- **Purpose**: Transforms discrete waypoints into a map-ready route.

### 4. GPT Agent (`ChatGPTAgent`)
- **Role**: Handles complex or fallback logic via OpenAI’s chat API.
- **Mechanism**:
  - Uses `openai-python` v1.x interface (`client.chat.completions.create`).
  - Generates or refines JSON waypoint arrays when procedural logic alone is insufficient.
- **Purpose**: Fills gaps for advanced constraints (e.g., extra waypoints for calorie goals).

### 5. Google Text Search Agent (`PlacesTextSearchClient`)
- **Role**: Enriches abstract stop names with real locations.
- **Mechanism**:
  - Queries Google Places Text Search API.
  - Returns top results with `name`, `formatted_address`, `latitude`, and `longitude`.
- **Purpose**: Maps user-specified stops ("sushi", "arcade") to actual venues.

### 6. Fitness Agent
- **Role**: Plans routes tailored to health metrics (steps, distance, calories).
- **Mechanism**:
  - Parses constraints like "10,000 steps" or "burn 100 calories".
  - Builds base route or loop via a nearby POI for step targets.
  - Estimates calories via MET × duration.
  - Invokes GPT Agent for additional waypoints if targets are unmet.
- **Purpose**: Turns fitness goals into actionable routes.

### 7. Fallback Agent
- **Role**: Covers all other intent types via GPT.
- **Mechanism**:
  - Pre-injects any GSR stops.
  - Prompts GPT for a JSON array of waypoints.
  - Merges and deduplicates the results.
- **Purpose**: Ensures no user request goes unanswered.

---

## Getting Started
1. **Clone** this repo  
2. **Install** dependencies:  
    ```bash
    pip install -r requirements.txt
    ```
3. **Set** your API keys:  
    ```bash
    # Set your API keys
    export GOOGLE_MAPS_API_KEY=your_google_maps_key_here
    export NVIDIA_API_KEY=your_nvidia_key_here

    # Install dependencies
    pip install -r requirements.txt

    # Run the server
    python main.py
    ```

## 🚀 NVIDIA Model Integration

This project has been refactored to use NVIDIA-based models instead of OpenAI GPT models for all agentic components:

### **Refactored Components:**

1. **FetchAI Intent Parser** → **NVIDIA Intent Parser**
   - Uses NVIDIA's `nvidia/llama3-8b-instruct` model
   - Handles natural language to structured intent conversion
   - Improved performance and cost efficiency

2. **GPT Agent** → **NVIDIA Agent**
   - Replaced OpenAI GPT-3.5-turbo with NVIDIA models
   - Specialized methods for different use cases:
     - `parse_intent()`: Intent classification
     - `plan_route()`: Route waypoint generation
     - `optimize_fitness_route()`: Fitness route optimization
     - `chat()`: General conversation

3. **Fallback Agent** → **NVIDIA-powered Fallback**
   - Uses NVIDIA models for route planning
   - Maintains same functionality with better performance

4. **Fitness Agent** → **NVIDIA-powered Fitness**
   - NVIDIA models for fitness route optimization
   - Enhanced calorie and step goal optimization

### **Benefits of NVIDIA Integration:**

- **Lower Latency**: Direct API calls to NVIDIA's infrastructure
- **Cost Reduction**: No per-token pricing from OpenAI
- **Better Performance**: Optimized models for specific tasks
- **Privacy**: Enhanced data privacy with NVIDIA's infrastructure
- **Scalability**: Better handling of concurrent requests

### **Model Selection:**

The refactoring uses NVIDIA's `nvidia/llama3-8b-instruct` model for all tasks, which provides:
- Excellent structured output capabilities
- Good performance on route planning tasks
- Consistent JSON generation
- Fast inference times

## 🔐 Environment Setup

Create a `.env` file or export environment variables:

```bash
# Required API Keys
export GOOGLE_MAPS_API_KEY=your_google_maps_key_here
export NVIDIA_API_KEY=your_nvidia_key_here

# Optional
export GOOGLE_API_KEY=your_google_places_key_here
```

⚠️ **Security Note**: Never commit API keys to version control. Always use environment variables.
