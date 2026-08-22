# Weather Parametric Insurance — GenLayer

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A decentralized weather parametric insurance application built around a
GenLayer Intelligent Contract. The project verifies a predefined weather
condition using external weather data and GenLayer consensus, records policy
evidence and state on-chain, and exposes an explicit policy and settlement
lifecycle.

## Contents

- [How it works](#how-it-works)
- [Contract constructor](#contract-constructor)
- [Weather source schema](#weather-source-schema)
- [Built-in weather adapter](#built-in-weather-adapter)
- [Prerequisites](#prerequisites)
- [Development workflow](#development-workflow)
- [Frontend](#frontend)
- [License](#license)

## How it works

1. **Explicit weather-source trust policy** — the policy stores one exact
   trusted weather-source URL and rejects evaluation requests using any
   other URL.
2. **Robust response handling** — the weather response is parsed as JSON,
   normalized into a small canonical record, and invalid or malformed
   responses are represented deterministically instead of leaking exception
   text into consensus.
3. **Consensus-verified decision** — GenLayer `prompt_comparative` checks
   the decision-critical fields, and the contract independently re-verifies
   the final threshold comparison.
4. **Policy lifecycle** — `ACTIVE → TRIGGERED / NOT_TRIGGERED / INVALID /
   EXPIRED → SETTLED`, with a renewable policy configuration.
5. **Funding + settlement state** — the contract accepts GEN funding,
   records funded balance, exposes payout eligibility, and records
   settlement references.

> `confirm_settlement()` records that an eligible policy has been settled.
> It is a settlement-state primitive, not a claim that money has already
> been paid to a policyholder. A production deployment can connect this
> state to a dedicated settlement vault or payout module — this separation
> keeps the insurance decision layer auditable and honest about what the
> contract has actually executed.

The contract lives at `contracts/WeatherParametricInsurance.py`.

## Contract constructor

`WeatherParametricInsurance` requires:

| Parameter | Type | Notes |
|---|---|---|
| `location` | `str` | e.g. `"Cape Town, South Africa"` |
| `threshold_temp` | `i32` | Tenths of a degree Celsius — `325` = 32.5°C |
| `trusted_weather_source` | `str` | Exact URL the contract will trust |
| `policy_duration_days` | `u32` | |
| `payout_amount` | `u256` | Wei — `1 GEN = 1_000_000_000_000_000_000` |

The deployer automatically becomes `policy_owner` and `policyholder`.

## Weather source schema

The trusted endpoint should return JSON shaped like:

```json
{
  "location": "Cape Town, South Africa",
  "temperature_c": 34.2,
  "observed_at": "2026-08-21T14:00:00Z"
}
```

The contract normalizes this response, asks GenLayer consensus to validate
the policy decision, and then independently re-verifies the threshold
comparison against the normalized reading.

> **Two things worth double-checking against the actual contract/adapter
> code before you demo this:**
> - This schema's `observed_at` includes seconds and a `Z` offset; the
>   adapter's own example below doesn't. Pick one canonical format and
>   confirm `/api/weather` actually returns it — an ambiguous timestamp is
>   a real problem for evidence you're recording on-chain.
> - The threshold comparison was previously documented as
>   `temperature_tenths_c > threshold_temp`, but this schema only defines
>   `temperature_c`. If the contract converts to tenths internally, it's
>   worth a one-line comment in the source saying so.

## Built-in weather adapter

The Next.js frontend includes `/api/weather`. It resolves a city through
the Open-Meteo geocoding service, requests current 2 m temperature from the
Open-Meteo forecast API, and returns the contract's required normalized
shape:

```json
{
  "location": "Cape Town, South Africa",
  "temperature_c": 24.1,
  "observed_at": "2026-08-21T14:00"
}
```

The adapter keeps those provider-specific details out of the Intelligent
Contract and gives the contract one stable, explicit source policy.

## Prerequisites

- Python 3.12+
- Node.js (for the frontend)
- A GenLayer network for integration tests and deployment — [GenLayer
  Studio](https://studio.genlayer.com) or a local node

## Development workflow

```bash
pip install -r requirements.txt

# Lint the contract with GenLayer's linter before deploying
# (see GenLayer's docs for the current command)

# Fast, in-memory tests — no Studio required
pytest tests/direct

# Integration tests against the network set in gltest.config.yaml (studionet)
gltest --network studionet
```

## Frontend

```bash
cd frontend
cp .env.example .env.local
# set NEXT_PUBLIC_GENLAYER_CONTRACT_ADDRESS
npm install
npm run dev
```

## License

MIT — see [LICENSE](./LICENSE).
