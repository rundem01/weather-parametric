import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from weather_api import fetch_weather

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/api/weather")
def weather(
    city: str = Query(
        ...,
        min_length=2,
        max_length=100,
        description="City label, e.g. Cape Town, South Africa",
    )
) -> JSONResponse:
    data = fetch_weather(city)
    return JSONResponse(
        content=data,
        headers={
            "Cache-Control": "no-store",
            "Access-Control-Allow-Origin": "*",
        },
    )
