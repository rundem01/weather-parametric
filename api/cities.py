import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from weather_api import CITIES

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/api/cities")
def cities() -> JSONResponse:
    return JSONResponse(
        content={
            "count": len(CITIES),
            "cities": [{"label": city} for city in CITIES],
        },
        headers={"Cache-Control": "no-store"},
    )
