# Weather Parametric Insurance — GenLayer DApp

A complete GenLayer Project submission: live weather adapter, Mochi-themed dashboard, and a **real GenLayerJS read/write path** to the deployed WeatherParametricInsurance Intelligent Contract.

## The reviewer requirement this build addresses

The prior submission was rejected because the browser calculated the trigger locally and never called the submitted contract.

This repository fixes that exact problem:

```text
Browser
  ↓
Read deployed contract with GenLayerJS
  ↓
Read policy + trusted weather source
  ↓
Test trusted source
  ↓
Wallet signs writeContract()
  ↓
evaluate_weather_trigger(trusted_source)
  ↓
GenLayer consensus
  ↓
FINALIZED receipt
  ↓
Read contract state again
  ↓
Display payout_triggered / verified / weather summary
```

The browser comparison is explicitly labeled **preview only**. It is not the final insurance decision.

## Complete structure

```text
.
├── api/
│   └── index.py
├── contracts/
│   └── WeatherParametricInsurance.py
├── public/
│   └── mochi.png
├── src/
│   ├── main.ts
│   ├── style.css
│   └── vite-env.d.ts
├── tests/
│   └── test_api.py
├── docs/
│   ├── API.md
│   ├── DEPLOYMENT.md
│   ├── GENLAYER_INTEGRATION.md
│   └── SUBMISSION_NOTES.md
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── weather_api.py
├── requirements.txt
├── pyproject.toml
├── deployment_inputs.json
├── .env.example
├── .gitignore
└── README.md
```

**There is intentionally no legacy `main.py`, root `dashboard.html`, root `style.css`, or custom `vercel.json`.**

Vercel's current Python + Vite deployment supports `api/index.py` as the FastAPI entrypoint and routes `/api/*` to that function. citeturn316946search0turn316946search2

## 1. Install

```bash
npm install
```

Python API dependencies:

```bash
python -m pip install -r requirements.txt
```

## 2. Configure

Copy:

```text
.env.example → .env.local
```

Set:

```env
VITE_GENLAYER_CONTRACT_ADDRESS=0xYOUR_DEPLOYED_CONTRACT
VITE_GENLAYER_NETWORK=studionet
```

The contract address must be the address of the contract deployed from:

```text
contracts/WeatherParametricInsurance.py
```

## 3. Verify the API

The app exposes:

```text
/api/health
/api/cities
/api/weather?city=Cape%20Town%2C%20South%20Africa
/api/docs
/api/redoc
/api/openapi.json
```

The API returns:

```json
{
  "location": "Cape Town, South Africa",
  "temperature_tenths_c": 241,
  "observed_at": "2026-08-26T12:00:00Z",
  "source": "Open-Meteo via Weather Parametric Insurance API"
}
```

The API deliberately returns the **exact requested city label** in `location` so the contract's exact policy-location check remains stable.

## 4. Deploy the contract

Constructor inputs:

```text
location
threshold_temp
trusted_weather_source
policy_duration_days
payout_amount
```

Example:

```text
location:
Cape Town, South Africa

threshold_temp:
325

trusted_weather_source:
https://YOUR-VERCEL-DOMAIN.vercel.app/api/weather?city=Cape%20Town%2C%20South%20Africa

policy_duration_days:
30

payout_amount:
1000
```

The URL is a policy trust boundary. The contract requires the submitted URL to equal the configured `trusted_weather_source`.

## 5. Deploy the web app

Import the repository root into Vercel.

Do **not** upload the project inside another nested project folder.

Vercel should build the Vite application and package `api/index.py` as the Python function. Current Vercel guidance uses this combined frontend + FastAPI layout and exposes the Python routes under `/api/*`. citeturn316946search0turn316946search1

## 6. Real GenLayer transaction flow

The dashboard performs:

```ts
const txHash = await writeClient.writeContract({
  address,
  functionName: "evaluate_weather_trigger",
  args: [policy.source],
  value: BigInt(0),
});

const receipt = await readClient.waitForTransactionReceipt({
  hash: txHash,
  status: TransactionStatus.FINALIZED,
});
```

It then checks the execution result before reading updated state. This follows GenLayer's documented GenLayerJS wallet/read/write/receipt pattern. citeturn557122search0turn557122search1

The connected wallet must be the policy owner because the contract enforces owner authorization.

## 7. Reviewer verification

A reviewer can verify the required path without trusting the UI:

1. Open the deployed app.
2. Connect the wallet that owns the deployed policy.
3. Click **Read contract**.
4. Confirm the location, threshold and trusted source come from the deployed contract.
5. Click **Test live weather**.
6. Click **Evaluate through GenLayer**.
7. Approve the wallet transaction.
8. Observe the transaction hash.
9. Wait for `FINALIZED`.
10. Confirm `payout_triggered`, `verified_by_consensus`, observed temperature, and summary are read back from the contract.

GenLayer documents that a transaction can be finalized while execution itself has failed, so the frontend explicitly checks the execution result before treating the state read as successful. citeturn557122search0turn557122search2
