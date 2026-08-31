# API Reference

## GET `/api/cities`
Returns the complete supported city list.

## GET `/api/weather?city=...`
Returns a canonical, signed weather record for consumption by the GenLayer
contract. The `city` parameter must match a label from `/api/cities` exactly.

```json
{
  "location": "Cape Town, South Africa",
  "temperature_tenths_c": 135,
  "observed_at": "2026-08-31T13:45",
  "issued_at": "2026-08-31T13:47",
  "source": "Open-Meteo via Weather Parametric Insurance API",
  "signature": "8f3a1c…512 hex chars…",
  "signature_alg": "RSA-PKCS1v15-SHA256"
}
```

The contract verifies `signature` against the public key registered at
deployment and rejects records where `issued_at − observed_at` exceeds 180
minutes (`OBSERVATION_STALE`).

## API documentation
`/api/docs` — full reference including the signing scheme, canonical message
format, and the on-chain validation checks.
