# Weather Parametric Insurance

A decentralized weather parametric insurance demo built on GenLayer Intelligent
Contracts. A policy is deployed on-chain with a location, a temperature
threshold, a coverage window, and a single trusted weather-source URL. When the
policy is evaluated, the contract itself fetches that source, has multiple
validators independently verify the reading through an LLM, reaches consensus on
whether the payout condition is met, and — on settlement — transfers the payout
to the policyholder.

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
   │
   ▼
confirm_settlement() → emit_transfer() → policyholder is paid
```

Three pieces:

| Piece | Location | Role |
|---|---|---|
| Intelligent Contract | `contracts/WeatherParametricInsurance.py` | Holds the policy, runs consensus evaluation, moves funds |
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

## Policy lifecycle

```
ACTIVE
  ├─ fund_policy()              deposit the payout amount
  └─ evaluate_weather_trigger() consensus decides the outcome
        ├─→ TRIGGERED      → confirm_settlement() → SETTLED  (payout transferred)
        ├─→ NOT_TRIGGERED  → withdraw_remaining()            (funding returned)
        └─→ INVALID        → withdraw_remaining()            (funding returned)
```

A policy can only be evaluated while `ACTIVE`, and only its owner may evaluate
or settle it. Once resolved, `withdraw_remaining` returns whatever balance is
left to the policy owner, so funding is never stranded regardless of outcome.

### Coverage window

Every policy carries an explicit UTC coverage window, supplied as constructor
arguments in `YYYY-MM-DDTHH:MM` form. After consensus, the contract compares the
observation's timestamp against that window. An observation outside it resolves
the policy to `INVALID` with `get_invalid_reason()` returning
`OBSERVATION_OUT_OF_WINDOW`, and no payout becomes eligible — however valid the
reading is in every other respect.

The bounds are constructor arguments rather than a derived chain timestamp for
two reasons: non-deterministic blocks cannot read storage, and taking "now" from
the same feed being validated would be circular.

Timestamps are normalized to minute precision before comparison. Sources vary
between `2026-08-28T05:45` and `2026-08-24T12:00:00Z`, and lexicographic
comparison across different lengths is unsound.

### Settlement and refunds

`confirm_settlement(reference)` requires status `TRIGGERED`, settlement status
`ELIGIBLE`, a non-empty reference, and a contract balance covering
`payout_amount`. It transfers the payout to the policyholder via
`gl.get_contract_at(...).emit_transfer(...)` and records it in `total_paid_out`.

The balance is checked rather than `total_funded`, because the balance is what
can actually be sent. `set_policyholder` nominates who receives the payout; it
defaults to the deployer.

`withdraw_remaining()` returns the remaining balance to the policy owner once a
policy has resolved, recording it in `total_refunded`. `renew_policy` refuses to
run while a balance remains, so funds cannot be orphaned by a reset.

---

## Using the demo

1. **Connect a wallet.** Requires an injected EVM wallet on GenLayer Studionet
   (chain `0xf22f` / 61999). The app will offer to add and switch to the network.
2. **Enter the contract address** and click *Read contract*. Policy fields,
   coverage window, funding status, and settlement accounting load from chain.
   This needs no wallet — reads are unsigned.
3. **Test live weather** (optional) fetches the contract's trusted source and
   shows what the browser thinks the answer would be. Preview only.
4. **Evaluate through GenLayer** submits `evaluate_weather_trigger()` as a real
   transaction. Approve it in your wallet, then wait — consensus typically takes
   one to three minutes.
5. **Read the result.** The on-chain decision, observed temperature, settlement
   status, and rejection reason all come from contract state after finalization.

> The connected wallet must be the one that deployed the policy.
> `evaluate_weather_trigger` and `confirm_settlement` both call
> `_require_owner()` and revert otherwise.

### Weather explorer

The lower section queries the adapter directly for any supported city. It is
independent of the contract and useful for confirming the adapter is healthy.

---

## Local development

```bash
npm install
npm run dev
```

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

No `vercel.json` is needed. A catch-all rewrite actively breaks this setup — see
*Routing* below.

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
| `coverage_start` | `2026-08-01T00:00` |
| `coverage_end` | `2026-08-31T23:59` |

After deploying, call `get_trusted_weather_source` and confirm it returns the
bare URL with nothing prepended, and check the coverage window brackets the
period you intend to test. A malformed trusted source cannot be corrected later
— `renew_policy` is blocked while the policy is `ACTIVE`, and the only exit from
`ACTIVE` is a successful evaluation, which a bad URL prevents. The policy would
need redeploying.

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
`trusted_weather_source ` followed by the URL. `fetch()` treated the whole string
as a relative path, resolved it against the app's origin, and got a 404 HTML page
— which surfaced in the UI as `Unexpected token 'T', "The page c"... is not valid
JSON`, since the code parsed the response before checking the status.

Verify `get_trusted_weather_source` returns a clean URL immediately after any
deployment.

### Receipt field naming

`waitForTransactionReceipt` returns an object whose execution-result field name
varies by node version. Reading a single camelCase property yielded `undefined`,
and comparing that against an expected constant reported failure on transactions
that had in fact succeeded — confirmed by `get_evaluation_count` incrementing and
`get_policy_status` moving to `NOT_TRIGGERED`.

`evaluateOnChain` now checks several possible field names and treats only an
explicit error value as a failure.

### Value transfers and SDK naming

`gl.ContractAt(...)` is the pre-0.1.3 name and raises `AttributeError` at
runtime on current runners. The current call is `gl.get_contract_at(...)`, which
works for both contracts and EOAs. Because the failure happens at execution
rather than deploy time, a contract using the old name deploys cleanly and only
fails when the transfer line is finally reached.

### Schema loading

A `__receive__` method annotated `-> None` prevented the contract schema from
loading in Studio, leaving no methods available to call. Removing it resolved the
issue; the documented form carries no return annotation.

### Chain ID

`STUDIONET_CHAIN_ID` was `0xf21f` (61983) while the correct value is `0xf22f`
(61999). The constant is used by the post-connection check, the
`wallet_switchEthereumChain` request, and the `chainChanged` guard, so one wrong
digit broke all three — presenting as `chainId should be same as current
chainId` with neither value named.

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
correct outcome. To see the trigger and settlement path, deploy a policy with a
threshold below the current temperature.

Contract state after an evaluation:

| Method | Meaning |
|---|---|
| `get_policy_status` | `ACTIVE`, `TRIGGERED`, `NOT_TRIGGERED`, `INVALID`, or `SETTLED` |
| `get_invalid_reason` | Why an evaluation was rejected, when status is `INVALID` |
| `get_payout_triggered` | Whether the payout condition was met |
| `get_verified_by_consensus` | Whether validators reached agreement |
| `get_evaluation_count` | Number of evaluations run |
| `get_last_observed_temp` | Temperature the contract acted on, in tenths |
| `get_last_observed_at` | Timestamp of the observation used |
| `get_coverage_start` / `get_coverage_end` | The policy's coverage window |
| `get_settlement_status` | `PENDING`, `ELIGIBLE`, `SETTLED`, or `NOT_APPLICABLE` |
| `get_total_paid_out` | Value transferred to the policyholder |
| `get_total_refunded` | Value returned to the policy owner |
| `get_contract_balance` | What the contract currently holds |
| `get_weather_summary` | Short factual summary from the evaluation |

Rejection reasons from `get_invalid_reason`:

| Reason | Meaning |
|---|---|
| `OBSERVATION_OUT_OF_WINDOW` | Observation timestamp fell outside the coverage window |
| `SOURCE_RECORD_INVALID` | The fetched record failed schema or range validation |
| `LOCATION_MISMATCH` | Observed location did not match the policy location |
| `TRIGGER_DECISION_MISMATCH` | Consensus decision disagreed with the deterministic threshold comparison |

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
