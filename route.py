import requests as req
import os
import json
from dotenv import load_dotenv

EMISSION_FACTOR = 0.271   # kg CO₂ per km (example vehicle)
FUEL_PRICE = 105          # INR per liter
MILEAGE = 15              # km per liter
VALUE_OF_TIME = 2         # INR per minute

def getRoutes(jsonPayload, header, url):
    response = req.post(url=url, json=jsonPayload, headers=header)
    response.raise_for_status()
    return response.json()

def extractData(respond):
    extracted = []

    routes = respond.get("routes", [])

    for idx, route in enumerate(routes):
        summary = route.get("summary", {})
        segments = route.get("segments", [])
        geometry = route.get("geometry")

        total_steps = 0
        turn_count = 0

        for segment in segments:
            for step in segment.get("steps", []):
                total_steps += 1
                if step.get("type") not in [10, 11]:  # ignore start & arrive
                    turn_count += 1

        extracted.append({
            "route_id": idx,
            "distance_km": round(summary.get("distance", 0) / 1000, 3),
            "duration_min": round(summary.get("duration", 0) / 60, 2),
            "steps": total_steps,
            "turns": turn_count,
            "geometry": geometry
        })

    return extracted

def normalize(values):
    mn, mx = min(values), max(values)
    return [(v - mn) / (mx - mn + 1e-6) for v in values]

def main():
    load_dotenv()

    url = "https://api.openrouteservice.org/v2/directions/driving-car"

    headers = {
        "Authorization": os.getenv("API"),
        "Content-Type": "application/json"
    }

    payload = {
        "coordinates": [
            # [78.17611956533857, 11.683720337350456], 
            # [78.13902764781922, 11.669020198322118]
            [77.27648723693109 , 11.497201492869667],
            [78.15923629719867 , 11.659103262290106]
        ],
        "alternative_routes": {
            "target_count": 3,
            "share_factor": 0.6
        }
    }

    response = getRoutes(payload, headers, url)

    with open("response.json", "w") as f:
        json.dump(response, f, indent=4)

    routes_data = extractData(response)

    for route in routes_data:
        # CO₂
        route["emissions_kg"] = round(
            route["distance_km"] * EMISSION_FACTOR, 3
        )

        fuel_cost = (route["distance_km"] / MILEAGE) * FUEL_PRICE
        time_cost = route["duration_min"] * VALUE_OF_TIME

        route["total_cost"] = round(fuel_cost + time_cost, 2)

    costs = normalize([r["total_cost"] for r in routes_data])
    co2s  = normalize([r["emissions_kg"] for r in routes_data])

    a, b = 0.5, 0.5 

    for i, r in enumerate(routes_data):
        r["score"] = round(a * costs[i] + b * co2s[i], 4)

    best_cost = min(routes_data, key=lambda x: x["total_cost"])
    best_eco  = min(routes_data, key=lambda x: x["emissions_kg"])
    best_mix  = min(routes_data, key=lambda x: x["score"])

    print("\nALL ROUTES:")
    for r in routes_data:
        print(json.dumps(r, indent=2))

    print("\nCHEAPEST ROUTE:")
    print(json.dumps(best_cost, indent=2))

    print("\nGREENEST ROUTE:")
    print(json.dumps(best_eco, indent=2))

    print("\nBEST BALANCED ROUTE:")
    print(json.dumps(best_mix, indent=2))


if __name__ == "__main__":
    main()