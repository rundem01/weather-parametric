from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from weather_api import CITIES, fetch_weather

app = FastAPI(
    title="Weather Parametric Insurance API",
    version="1.0.0",
    summary="Trusted weather-data adapter for the GenLayer insurance contract",
    description="""
# Weather Parametric Insurance API

This service resolves a requested city through Open-Meteo, retrieves its
current temperature, and returns the exact canonical record expected by
the GenLayer Intelligent Contract.

## Canonical record

```json
{
  "location": "Cape Town, South Africa",
  "temperature_tenths_c": 241,
  "observed_at": "2026-08-26T12:00:00Z"
}
```

`241` means `24.1°C`.

## Trust boundary

The deployed GenLayer policy stores an exact trusted-source URL.
The frontend reads that URL directly from the contract and submits the
same URL to `evaluate_weather_trigger()`.

The browser's weather comparison is only a preview. The contract is the
source of truth for the final policy decision.
""",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


@app.get("/api/health", tags=["System"], summary="Check API health")
def health() -> dict:
    return {
        "ok": True,
        "service": "weather-parametric-insurance",
        "version": "1.0.0",
    }


@app.get(
    "/api/cities",
    tags=["Weather"],
    summary="List supported global cities",
)
def cities() -> dict:
    return {
        "count": len(CITIES),
        "cities": [{"label": city} for city in CITIES],
    }


@app.get(
    "/api/weather",
    tags=["Weather"],
    summary="Get current weather for a city",
    response_description="Canonical weather observation for GenLayer",
)
def weather(
    city: str = Query(
        ...,
        min_length=2,
        max_length=100,
        description="City label, e.g. Cape Town, South Africa",
        examples=["Cape Town, South Africa"],
    )
) -> JSONResponse:
    data = fetch_weather(city)
    return JSONResponse(
        content=data,
        headers={"Cache-Control": "no-store"},
    )
