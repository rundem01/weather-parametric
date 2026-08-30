import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from weather_api import fetch_weather

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# PEM-encoded PKCS#8 private key, set in Vercel as an environment variable.
# Newlines may be stored either literally or escaped as \n.
SIGNING_KEY_PEM = os.environ.get("WEATHER_SIGNING_KEY_PEM", "").replace("\\n", "\n")


def canonical_message(
    location: str, temperature_tenths_c: int, observed_at: str
) -> bytes:
    """
    The exact bytes that get signed. Key order and separators are fixed and
    must match the contract's _canonical_message byte for byte — any drift
    here invalidates every signature the contract sees.
    """
    return json.dumps(
        {
            "location": location,
            "temperature_tenths_c": temperature_tenths_c,
            "observed_at": observed_at,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sign_observation(record: dict) -> str:
    """Return a hex-encoded RSA PKCS#1 v1.5 / SHA-256 signature."""
    if not SIGNING_KEY_PEM:
        raise HTTPException(
            status_code=503,
            detail="WEATHER_SIGNING_KEY_PEM is not configured on the server.",
        )

    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    key = serialization.load_pem_private_key(
        SIGNING_KEY_PEM.encode("utf-8"), password=None
    )

    message = canonical_message(
        record["location"],
        int(record["temperature_tenths_c"]),
        record["observed_at"],
    )
    return key.sign(message, padding.PKCS1v15(), hashes.SHA256()).hex()


@app.get("/api/weather")
def weather(
    city: str = Query(
        ...,
        min_length=2,
        max_length=100,
        description="City label, e.g. Cape Town, South Africa",
    )
) -> JSONResponse:
    record = fetch_weather(city)
    record["signature"] = sign_observation(record)
    record["signature_alg"] = "RSA-PKCS1v15-SHA256"

    return JSONResponse(
        content=record,
        headers={
            "Cache-Control": "no-store",
            "Access-Control-Allow-Origin": "*",
        },
    )
