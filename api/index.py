import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from weather_api import CITIES, fetch_weather

app = FastAPI(
    title="Weather Parametric Insurance API",
    version="1.1.0",
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

`241` means `24.1C`.

## Trust boundary

The deployed GenLayer policy stores an exact trusted-source URL.
The frontend reads that URL directly from the contract and submits the
same URL to `evaluate_weather_trigger()`.

The browser's weather comparison is only a preview. The contract is the
source of truth for the final policy decision.

## Evaluation flow

GenLayer consensus takes longer than a serverless request may run, so
evaluation is split in two:

1. `POST /api/evaluate` submits the transaction and returns its hash.
2. `GET /api/evaluate/{transaction_hash}` reports the current status.

Poll step 2 until `settled` is true.
""",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


# --------------------------------------------------------------------------
# Configuration (set these in Vercel: Project Settings -> Environment Variables)
# --------------------------------------------------------------------------

CONTRACT_ADDRESS = os.environ.get("GENLAYER_CONTRACT_ADDRESS", "")
PRIVATE_KEY = os.environ.get("GENLAYER_PRIVATE_KEY", "")
CHAIN_NAME = os.environ.get("GENLAYER_CHAIN", "testnet_asimov")


def _get_client_and_account():
    """Build a GenLayer client on demand.

    Imported lazily so the weather endpoints keep working even if the
    GenLayer SDK or its environment variables are missing.
    """
    if not CONTRACT_ADDRESS:
        raise HTTPException(
            status_code=503,
            detail="GENLAYER_CONTRACT_ADDRESS is not configured on the server.",
        )
    if not PRIVATE_KEY:
        raise HTTPException(
            status_code=503,
            detail="GENLAYER_PRIVATE_KEY is not configured on the server.",
        )

    try:
        from genlayer_py import create_account, create_client
        from genlayer_py import chains
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"genlayer-py is not installed: {exc}",
        ) from exc

    chain = getattr(chains, CHAIN_NAME, None)
    if chain is None:
        available = [n for n in dir(chains) if not n.startswith("_")]
        raise HTTPException(
            status_code=500,
            detail=f"Unknown chain '{CHAIN_NAME}'. Available: {available}",
        )

    account = create_account(account_private_key=PRIVATE_KEY)
    client = create_client(chain=chain, account=account)
    return client, account


# --------------------------------------------------------------------------
# System
# --------------------------------------------------------------------------

@app.get("/api/health", tags=["System"], summary="Check API health")
def health() -> dict:
    return {
        "ok": True,
        "service": "weather-parametric-insurance",
        "version": "1.1.0",
        "genlayer_configured": bool(CONTRACT_ADDRESS and PRIVATE_KEY),
        "chain": CHAIN_NAME,
    }


# --------------------------------------------------------------------------
# Weather
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# Contract
# --------------------------------------------------------------------------

class EvaluateRequest(BaseModel):
    weather_source: str | None = None


@app.get(
    "/api/policy",
    tags=["Contract"],
    summary="Read the deployed policy state",
)
def policy() -> dict:
    client, _ = _get_client_and_account()
    try:
        state = client.read_contract(
            address=CONTRACT_ADDRESS,
            function_name="get_policy_state",
            args=[],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Contract read failed: {exc}",
        ) from exc

    return {"address": CONTRACT_ADDRESS, "state": state}


@app.post(
    "/api/evaluate",
    tags=["Contract"],
    summary="Submit evaluate_weather_trigger() to the contract",
    response_description="Transaction hash; poll /api/evaluate/{hash} for the result",
)
def evaluate(body: EvaluateRequest | None = None) -> dict:
    client, account = _get_client_and_account()

    args = [body.weather_source] if body and body.weather_source else []

    try:
        transaction_hash = client.write_contract(
            address=CONTRACT_ADDRESS,
            function_name="evaluate_weather_trigger",
            args=args,
            value=0,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Contract write failed: {exc}",
        ) from exc

    return {
        "submitted": True,
        "transaction_hash": str(transaction_hash),
        "sender": str(getattr(account, "address", "")),
        "poll": f"/api/evaluate/{transaction_hash}",
    }


@app.get(
    "/api/evaluate/{transaction_hash}",
    tags=["Contract"],
    summary="Check the status of a submitted evaluation",
)
def evaluate_status(transaction_hash: str) -> dict:
    client, _ = _get_client_and_account()

    try:
        tx = client.get_transaction(transaction_hash=transaction_hash)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not fetch transaction: {exc}",
        ) from exc

    status = tx.get("status") or tx.get("status_name")
    execution = tx.get("tx_execution_result_name")

    settled = status in ("ACCEPTED", "FINALIZED")
    succeeded = execution == "FINISHED_WITH_RETURN"

    return {
        "transaction_hash": transaction_hash,
        "status": status,
        "execution_result": execution,
        "settled": settled,
        "succeeded": succeeded,
        "consensus_result": tx.get("consensus_result"),
        "return_value": tx.get("result") or tx.get("return_value"),
    }
