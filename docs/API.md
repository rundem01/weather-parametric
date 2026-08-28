# API Reference

## GET `/api/health`

Returns service status.

## GET `/api/cities`

Returns the complete supported city list.

## GET `/api/weather?city=...`

Returns the canonical weather record consumed by the GenLayer contract.

Example:

```json
{
  "location": "Cape Town, South Africa",
  "temperature_tenths_c": 241,
  "observed_at": "2026-08-26T12:00:00Z",
  "source": "Open-Meteo via Weather Parametric Insurance API"
}
```

## Interactive docs

- `/api/docs` — Swagger UI
- `/api/redoc` — ReDoc
- `/api/openapi.json` — OpenAPI document
