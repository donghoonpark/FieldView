import asyncio
import aiohttp
import json
import os

# Coordinates for US State Capitals (Lat, Lon)
# Excluding AK and HI as per project context
STATE_CAPITALS_COORDS = {
    "AL": (32.3777, -86.3006),  # Montgomery
    "AZ": (33.4484, -112.0740),  # Phoenix
    "AR": (34.7465, -92.2896),  # Little Rock
    "CA": (38.5816, -121.4944),  # Sacramento
    "CO": (39.7392, -104.9903),  # Denver
    "CT": (41.7637, -72.6851),  # Hartford
    "DE": (39.1582, -75.5244),  # Dover
    "FL": (30.4383, -84.2807),  # Tallahassee
    "GA": (33.7490, -84.3880),  # Atlanta
    "ID": (43.6150, -116.2023),  # Boise
    "IL": (39.7817, -89.6501),  # Springfield
    "IN": (39.7684, -86.1581),  # Indianapolis
    "IA": (41.5868, -93.6250),  # Des Moines
    "KS": (39.0473, -95.6752),  # Topeka
    "KY": (38.2009, -84.8733),  # Frankfort
    "LA": (30.4515, -91.1871),  # Baton Rouge
    "ME": (44.3106, -69.7795),  # Augusta
    "MD": (38.9784, -76.4922),  # Annapolis
    "MA": (42.3601, -71.0589),  # Boston
    "MI": (42.7325, -84.5555),  # Lansing
    "MN": (44.9537, -93.0900),  # Saint Paul
    "MS": (32.2988, -90.1848),  # Jackson
    "MO": (38.5767, -92.1735),  # Jefferson City
    "MT": (46.5891, -112.0391),  # Helena
    "NE": (40.8136, -96.7026),  # Lincoln
    "NV": (39.1638, -119.7674),  # Carson City
    "NH": (43.2081, -71.5375),  # Concord
    "NJ": (40.2206, -74.7597),  # Trenton
    "NM": (35.6870, -105.9378),  # Santa Fe
    "NY": (42.6526, -73.7562),  # Albany
    "NC": (35.7796, -78.6382),  # Raleigh
    "ND": (46.8083, -100.7837),  # Bismarck
    "OH": (39.9612, -82.9988),  # Columbus
    "OK": (35.4676, -97.5164),  # Oklahoma City
    "OR": (44.9429, -123.0351),  # Salem
    "PA": (40.2732, -76.8867),  # Harrisburg
    "RI": (41.8240, -71.4128),  # Providence
    "SC": (34.0007, -81.0348),  # Columbia
    "SD": (44.3668, -100.3538),  # Pierre
    "TN": (36.1627, -86.7816),  # Nashville
    "TX": (30.2672, -97.7431),  # Austin
    "UT": (40.7608, -111.8910),  # Salt Lake City
    "VT": (44.2601, -72.5754),  # Montpelier
    "VA": (37.5407, -77.4360),  # Richmond
    "WA": (47.0379, -122.9007),  # Olympia
    "WV": (38.3498, -81.6326),  # Charleston
    "WI": (43.0731, -89.4012),  # Madison
    "WY": (41.1399, -104.8202),  # Cheyenne
}

HEADERS = {
    "User-Agent": "(fieldview-app, contact@example.com)",
    "Accept": "application/geo+json",
}


async def fetch_url(session, url):
    async with session.get(url, headers=HEADERS) as response:
        if response.status == 200:
            return await response.json()
        else:
            # print(f"Error fetching {url}: {response.status}")
            return None


async def fetch_state_weather(session, state_code, lat, lon):
    try:
        # 1. Get Point Metadata
        points_url = f"https://api.weather.gov/points/{lat},{lon}"
        point_data = await fetch_url(session, points_url)

        if not point_data:
            return state_code, None

        # 2. Get Observation Stations
        stations_url = point_data["properties"]["observationStations"]
        stations_data = await fetch_url(session, stations_url)

        if not stations_data or not stations_data.get("features"):
            return state_code, None

        # Use the first station
        station_id = stations_data["features"][0]["properties"]["stationIdentifier"]

        # 3. Get Latest Observation
        obs_url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
        obs_data = await fetch_url(session, obs_url)

        if not obs_data:
            return state_code, None

        temp_c = obs_data["properties"]["temperature"]["value"]

        if temp_c is not None:
            print(f"{state_code}: {temp_c}°C (Station: {station_id})")
            return state_code, temp_c
        else:
            print(f"{state_code}: Temperature data unavailable for {station_id}")
            return state_code, None

    except Exception as e:
        print(f"Exception fetching data for {state_code}: {e}")
        return state_code, None


async def main():
    weather_data = {}
    print("Fetching weather data from NWS API (Async)...")

    async with aiohttp.ClientSession() as session:
        tasks = []
        for state_code, (lat, lon) in STATE_CAPITALS_COORDS.items():
            tasks.append(fetch_state_weather(session, state_code, lat, lon))

        results = await asyncio.gather(*tasks)

        for state_code, temp in results:
            if temp is not None:
                weather_data[state_code] = temp

    # Save to JSON
    output_path = os.path.join(
        os.path.dirname(__file__), "..", "examples", "us_weather_data.json"
    )
    with open(output_path, "w") as f:
        json.dump(weather_data, f, indent=4)

    print(f"\nWeather data saved to {output_path}")
    print(f"Successfully fetched data for {len(weather_data)} states.")


if __name__ == "__main__":
    asyncio.run(main())
