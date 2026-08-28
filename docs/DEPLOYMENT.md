# Deployment

## Vercel

Upload the repository root to Vercel.

Do not place the repository inside an extra nested directory.

Vercel serves:

- Vite frontend at `/`
- FastAPI under `/api/*`

## GenLayer

Deploy the canonical contract:

`contracts/WeatherParametricInsurance.py`

Record the deployed contract address and put it in:

```env
VITE_GENLAYER_CONTRACT_ADDRESS=0x...
VITE_GENLAYER_NETWORK=studionet
```

The trusted weather source must use the deployed Vercel domain:

```text
https://YOUR-DOMAIN.vercel.app/api/weather?city=Cape%20Town%2C%20South%20Africa
```

The browser reads this value from the deployed contract, then passes the exact same value into `evaluate_weather_trigger()`.
