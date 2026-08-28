# Weather Parametric Insurance

A decentralized weather parametric insurance demo built on GenLayer Intelligent
Contracts. A policy is deployed on-chain with a location, a temperature
threshold, and a single trusted weather-source URL. When the policy is
evaluated, the contract itself fetches that source, has multiple validators
independently verify the reading through an LLM, and reaches consensus on
whether the payout condition is met.

The browser never decides the outcome. It submits a transaction and reads the
result back from chain.

**Live demo:** https://weather-parametric-real.vercel.app

---

## How it works

```
Browser (Vite + TypeScript)
   │
   │  genlayer-js + injected wallet
   ▼
GenLayer Studionet ──── evaluate_weather_trigger(url)
   │                          │
   │                          │  gl.nondet.web.get(trusted_source)
   │                          ▼
   │                    Weather adapter (FastAPI on Vercel)
   │                          │
   │                          ▼
   │                    Open-Meteo
   │
   ▼
Validators independently fetch + evaluate → consensus → contract state
```

Three pieces:

| Piece | Location | Role |
|---|---|---|
| Intelligent Contract | `contracts/WeatherParametricInsurance.py` | Holds the policy, runs consensus evaluation, stores the decision |
| Weather adapter | `api/weather.py`, `api/cities.py` | Normalizes Open-Meteo into the canonical record the contract expects |
| Frontend | `src/main.ts` | Wallet connection, contract reads, transaction submission |

### Canonical weather record

The adapter returns exactly this shape. The contract depends on it.

```json
{
  "location": "Cape Town, South Africa",
  "temperature_tenths_c": 135,
  "observed_at": "2026-08-28T05:45",
  "source": "Open-Meteo via Weather Parametric Insurance API"
}
```

Temperatures are integer tenths of a degree Celsius — `135` means 13.5°C.
Integers avoid floating-point disagreement between validators.

---

## Using the demo

1. **Connect a wallet.** The app requires an injected EVM wallet on GenLayer
   Studionet (chain `0xf21f`). It will offer to add and switch to the network
   for you.
2. **Enter the contract address** and click *Read contract*. Policy location,
   threshold, trusted source, and status load directly from chain. This step
   needs no wallet — reads are unsigned.
3. **Test live weather** (optional) fetches the contract's trusted source and
   shows what the browser thinks the answer would be. This is a preview only.
4. **Evaluate through GenLayer** submits `evaluate_weather_trigger()` as a real
   transaction. Approve it in your wallet, then wait — consensus typically takes
   one to three minutes.
5. **Read the result.** The on-chain decision, observed temperature, and
   consensus flag come from contract state after finalization.

> The connected wallet must be the one that deployed the policy.
> `evaluate_weather_trigger` calls `_require_owner()` and will revert otherwise.

### Weather explorer

The lower section queries the adapter directly for any supported city. It is
independent of the contract and useful for confirming the adapter is healthy.

---

## Local development

```bash
npm install
npm run dev
```

The frontend expects the API on the same origin. For local work against the
deployed adapter, point the contract's trusted source at the production URL.

### Environment variables

| Variable | Purpose |
|---|---|
| `VITE_GENLAYER_CONTRACT_ADDRESS` | Pre-fills the contract address field |
| `VITE_GENLAYER_NETWORK` | Display label for the network badge |

`VITE_` variables are inlined at build time. Changing one in Vercel requires a
redeploy before it takes effect.

---

## Deployment

### Frontend and API

Vercel builds the Vite app and serves each file in `api/` as its own Python
serverless function. `api/weather.py` maps to `/api/weather`, `api/cities.py` to
`/api/cities`.

No `vercel.json` is needed. A catch-all rewrite actively breaks this setup —
see *Routing* below.

### Contract

Deploy through [GenLayer Studio](https://studio.genlayer.com) with these
constructor arguments:

| Argument | Example |
|---|---|
| `location` | `Cape Town, South Africa` |
| `threshold_temp` | `325` (32.5°C, in tenths) |
| `trusted_weather_source` | `https://weather-parametric-real.vercel.app/api/weather?city=Cape%20Town%2C%20South%20Africa` |
| `policy_duration_days` | `30` |
| `payout_amount` | `1000` |

After deploying, call `get_trusted_weather_source` and confirm it returns the
bare URL with nothing prepended. A malformed value here cannot be corrected
later — `renew_policy` is blocked while the policy is `ACTIVE`, and the only
exit from `ACTIVE` is a successful evaluation, which a bad URL prevents. The
policy would need redeploying.

---

## Notes on things that were fixed

Recorded because each was non-obvious and each would recur.

### Routing

`api/index.py` under Vercel's zero-config maps only to `/api/index`, so
`/api/weather` returned a platform 404. Adding a catch-all rewrite made things
worse rather than better: Vercel rewrites change the path the function receives,
so every request arrived at FastAPI as `/api/index` and matched no route,
producing `{"detail":"Not Found"}` for everything.

The working arrangement is one file per endpoint and no rewrite at all.

### Trusted source stored with its field name

The deployed policy's `trusted_weather_source` contained the literal text
`trusted_weather_source ` followed by the URL. `fetch()` treated the whole
string as a relative path, resolved it against the app's origin, and got a 404
HTML page — which surfaced in the UI as `Unexpected token 'T', "The page c"...
is not valid JSON`, since the code parsed the response as JSON before checking
the status.

Verify `get_trusted_weather_source` returns a clean URL immediately after any
deployment.

### Receipt field naming

`waitForTransactionReceipt` returns an object whose execution-result field name
varies by node version. Reading a single camelCase property yielded `undefined`,
and comparing that against an expected constant reported failure on
transactions that had in fact succeeded — confirmed by `get_evaluation_count`
incrementing and `get_policy_status` moving to `NOT_TRIGGERED`.

`evaluateOnChain` now checks several possible field names and treats only an
explicit error value as a failure, rather than treating anything unrecognized
as one.

### Wallet state on reload

Wallet approval persists per origin, but the UI only updated on click, so a
reload showed *Connect wallet* despite an active connection.
`restoreWalletConnection()` now calls `eth_accounts` on load — which returns
approved accounts without prompting — and restores the button, badge, and write
client when the wallet is present and on the correct chain.

---

## Reading a result

A finalized transaction with no payout is a working demo, not a failure. Cape
Town in August sits well below a 32.5°C threshold, so `NOT_TRIGGERED` is the
correct outcome. To see the trigger path, deploy a policy with a threshold below
the current temperature, or point it at a city that is currently hot.

Contract state after a successful evaluation:

| Method | Meaning |
|---|---|
| `get_policy_status` | `TRIGGERED`, `NOT_TRIGGERED`, or `INVALID` |
| `get_payout_triggered` | Whether the payout condition was met |
| `get_verified_by_consensus` | Whether validators reached agreement |
| `get_evaluation_count` | Number of evaluations run |
| `get_last_observed_temp` | Temperature the contract acted on, in tenths |
| `get_weather_summary` | Short factual summary from the evaluation |

---

## Project layout

```
api/
  weather.py       GET /api/weather?city=...
  cities.py        GET /api/cities
contracts/
  WeatherParametricInsurance.py
src/
  main.ts          Frontend logic
  style.css
weather_api.py     Open-Meteo client and city list
deployment_inputs.json
```
