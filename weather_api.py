from __future__ import annotations

from datetime import datetime, timezone
from json import JSONDecodeError, loads
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import HTTPException

OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 10
USER_AGENT = "WeatherParametricInsurance/1.0 (GenLayer DApp)"

CITIES = sorted(
    {
        "Abidjan, Côte d’Ivoire", "Accra, Ghana", "Addis Ababa, Ethiopia",
        "Algiers, Algeria", "Amman, Jordan", "Amsterdam, Netherlands",
        "Antananarivo, Madagascar", "Athens, Greece", "Auckland, New Zealand",
        "Baghdad, Iraq", "Baku, Azerbaijan", "Bamako, Mali", "Bangkok, Thailand",
        "Barcelona, Spain", "Beijing, China", "Beirut, Lebanon", "Belgrade, Serbia",
        "Berlin, Germany", "Bogotá, Colombia", "Boston, USA", "Bratislava, Slovakia",
        "Brussels, Belgium", "Bucharest, Romania", "Budapest, Hungary",
        "Buenos Aires, Argentina", "Cairo, Egypt", "Cape Town, South Africa",
        "Casablanca, Morocco", "Chennai, India", "Chicago, USA",
        "Christchurch, New Zealand", "Copenhagen, Denmark", "Dakar, Senegal",
        "Dar es Salaam, Tanzania", "Delhi, India", "Dhaka, Bangladesh",
        "Doha, Qatar", "Dubai, UAE", "Dublin, Ireland", "Durban, South Africa",
        "Edinburgh, UK", "Frankfurt, Germany", "Geneva, Switzerland",
        "Hanoi, Vietnam", "Harare, Zimbabwe", "Helsinki, Finland",
        "Ho Chi Minh City, Vietnam", "Hong Kong", "Honolulu, USA", "Houston, USA",
        "Istanbul, Türkiye", "Jakarta, Indonesia", "Johannesburg, South Africa",
        "Kabul, Afghanistan", "Kampala, Uganda", "Karachi, Pakistan",
        "Kathmandu, Nepal", "Kigali, Rwanda", "Kingston, Jamaica",
        "Kuala Lumpur, Malaysia", "Kuwait City, Kuwait", "Lagos, Nigeria",
        "Lima, Peru", "Lisbon, Portugal", "London, UK", "Los Angeles, USA",
        "Luanda, Angola", "Luxembourg, Luxembourg", "Madrid, Spain",
        "Manila, Philippines", "Maputo, Mozambique", "Melbourne, Australia",
        "Mexico City, Mexico", "Miami, USA", "Milan, Italy", "Minsk, Belarus",
        "Mogadishu, Somalia", "Monaco, Monaco", "Montreal, Canada", "Mumbai, India",
        "Munich, Germany", "Nairobi, Kenya", "Nassau, Bahamas", "New York, USA",
        "Nice, France", "Osaka, Japan", "Oslo, Norway", "Ottawa, Canada",
        "Panama City, Panama", "Paris, France", "Perth, Australia",
        "Port Louis, Mauritius", "Prague, Czechia", "Reykjavik, Iceland",
        "Rio de Janeiro, Brazil", "Riyadh, Saudi Arabia", "Rome, Italy",
        "San Francisco, USA", "Santiago, Chile", "São Paulo, Brazil",
        "Seattle, USA", "Seoul, South Korea", "Shanghai, China", "Singapore",
        "Sofia, Bulgaria", "Stockholm, Sweden", "Sydney, Australia", "Taipei, Taiwan",
        "Tallinn, Estonia", "Tehran, Iran", "Tel Aviv, Israel", "Tokyo, Japan",
        "Toronto, Canada", "Tunis, Tunisia", "Vancouver, Canada", "Vienna, Austria",
        "Vilnius, Lithuania", "Warsaw, Poland", "Washington, DC, USA",
        "Wellington, New Zealand", "Windhoek, Namibia", "Winnipeg, Canada",
        "Yangon, Myanmar", "Yerevan, Armenia", "Zagreb, Croatia", "Zurich, Switzerland",
        # additional major cities
        "Alexandria, Egypt", "Atlanta, USA", "Austin, USA", "Baltimore, USA",
        "Bengaluru, India", "Birmingham, UK", "Bordeaux, France", "Calgary, Canada",
        "Canberra, Australia", "Caracas, Venezuela", "Charlotte, USA", "Cologne, Germany",
        "Colombo, Sri Lanka", "Córdoba, Argentina", "Dallas, USA", "Detroit, USA",
        "Fes, Morocco", "Florence, Italy", "Fukuoka, Japan", "Guadalajara, Mexico",
        "Guatemala City, Guatemala", "Guayaquil, Ecuador", "Hamburg, Germany",
        "Hangzhou, China", "Havana, Cuba", "Ho Chi Minh City, Vietnam",
        "Hyderabad, India", "Indianapolis, USA", "Izmir, Türkiye", "Kansas City, USA",
        "Kraków, Poland", "Las Vegas, USA", "Leeds, UK", "Lyon, France",
        "Manchester, UK", "Marseille, France", "Medellín, Colombia", "Minneapolis, USA",
        "Mombasa, Kenya", "New Orleans, USA", "Orlando, USA", "Palermo, Italy",
        "Philadelphia, USA", "Phoenix, USA", "Pittsburgh, USA", "Porto, Portugal",
        "Portland, USA", "Quebec City, Canada", "Quito, Ecuador", "Recife, Brazil",
        "Rotterdam, Netherlands", "Sacramento, USA", "San Antonio, USA",
        "San Diego, USA", "San José, Costa Rica", "Santa Cruz de la Sierra, Bolivia",
        "Sendai, Japan", "Shenzhen, China", "St. Louis, USA", "Surabaya, Indonesia",
        "Tbilisi, Georgia", "Tijuana, Mexico", "Toulouse, France", "Valencia, Spain",
        "Vancouver, Canada", "Verona, Italy", "Winnipeg, Canada", "Xiamen, China",
    }
)


def _get_json(url: str) -> dict:
    request = Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            data = loads(response.read().decode("utf-8"))
            if not isinstance(data, dict):
                raise HTTPException(502, "upstream_invalid_response")
            return data
    except HTTPError as exc:
        raise HTTPException(502, f"upstream_http_error:{exc.code}") from exc
    except URLError as exc:
        raise HTTPException(502, "upstream_connection_error") from exc
    except TimeoutError as exc:
        raise HTTPException(504, "upstream_timeout") from exc
    except (JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(502, "upstream_invalid_json") from exc


def normalize_city(city: str) -> str:
    return " ".join(city.strip().split())


def resolve_city(city: str) -> dict:
    # Use the city name portion for geocoding when the UI label contains a country suffix.
    search_name = city.split(",", 1)[0].strip()

    url = (
        f"{OPEN_METEO_GEOCODING_URL}"
        f"?name={quote(search_name)}&count=5&language=en&format=json"
    )
    payload = _get_json(url)
    results = payload.get("results") or []

    if not results:
        raise HTTPException(404, "city_not_found")

    # Prefer a country match when the caller provided one.
    requested_country = city.split(",", 1)[1].strip().lower() if "," in city else ""
    chosen = results[0]

    if requested_country:
        for item in results:
            candidate = str(item.get("country") or "").lower()
            if requested_country in candidate or candidate in requested_country:
                chosen = item
                break

    if chosen.get("latitude") is None or chosen.get("longitude") is None:
        raise HTTPException(502, "geocoding_missing_coordinates")

    return chosen


def fetch_weather(city: str) -> dict:
    normalized = normalize_city(city)
    if len(normalized) < 2:
        raise HTTPException(400, "city_required")

    place = resolve_city(normalized)

    url = (
        f"{OPEN_METEO_FORECAST_URL}"
        f"?latitude={quote(str(place['latitude']))}"
        f"&longitude={quote(str(place['longitude']))}"
        f"&current=temperature_2m"
        f"&timezone=UTC"
    )
    payload = _get_json(url)
    current = payload.get("current") or {}
    temperature_c = current.get("temperature_2m")

    if not isinstance(temperature_c, (int, float)) or isinstance(temperature_c, bool):
        raise HTTPException(502, "weather_temperature_missing")

    observed_at = current.get("time") or (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    # Preserve the exact user policy label. This is critical because the contract
    # enforces an exact location match.
    return {
        "location": normalized,
        "temperature_tenths_c": int(round(float(temperature_c) * 10)),
        "observed_at": str(observed_at),
        "source": "Open-Meteo via Weather Parametric Insurance API",
    }
