# Submission Notes

## What it does

Weather Parametric Insurance is a GenLayer Project that connects a live weather API to a deployed Intelligent Contract. A policy defines a city and a temperature threshold. The application reads the policy from the deployed contract, retrieves the contract's trusted weather-source URL, and submits a signed `evaluate_weather_trigger()` transaction through GenLayerJS.

## Problem it solves

Weather insurance normally requires an external process to determine whether a measurable condition occurred. This project demonstrates a programmable alternative: a predefined weather parameter can be evaluated through GenLayer consensus and recorded directly in contract state.

## How to use it

1. Deploy the Vercel application.
2. Confirm `/api/health` and `/api/weather`.
3. Deploy `WeatherParametricInsurance.py`.
4. Configure the exact deployed `/api/weather?...` URL as `trusted_weather_source`.
5. Put the deployed contract address in `.env.local`.
6. Open the dashboard.
7. Connect the policy-owner wallet.
8. Read the contract.
9. Test the trusted weather source.
10. Submit **Evaluate through GenLayer**.
11. Approve the wallet transaction.
12. Wait for `FINALIZED`.
13. Confirm the dashboard displays the state read back from the contract.

## Important scope

The current policy records the verified trigger and settlement state. It does not claim that a cash payout has occurred merely because `payout_triggered` is true.

## Reviewer evidence

The important evidence is the actual transaction path:

```text
Dashboard
→ GenLayerJS writeContract
→ evaluate_weather_trigger
→ GenLayer consensus
→ finalized transaction
→ read contract state
```

The browser weather comparison is only a preview and is not used as the source of truth for the final decision.
