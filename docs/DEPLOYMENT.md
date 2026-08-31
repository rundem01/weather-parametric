# Deployment

## Vercel
Push the repository root to Vercel. Do not place it inside a nested directory.

Vercel serves:
- Vite frontend at `/`
- FastAPI functions under `/api/*` — one file per endpoint, no rewrite needed

Set these environment variables in Vercel's dashboard before deploying:

| Variable | Value |
|---|---|
| `VITE_GENLAYER_CONTRACT_ADDRESS` | Deployed contract address (pre-fills the UI field) |
| `VITE_GENLAYER_NETWORK` | `studionet` |
| `WEATHER_SIGNING_KEY_PEM` | PEM-encoded RSA private key (server-side only — never commit this) |

## GenLayer
Deploy `contracts/WeatherParametricInsurance.py` through GenLayer Studio.

Two constructor arguments depend on the deployed Vercel domain:

**`https://weather-parametric-real.vercel.app/api/weather?city=Cape%20Town%2C%20South%20Africa`**
