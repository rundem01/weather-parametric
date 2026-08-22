# Weather Parametric Insurance Frontend

## Setup

```bash
cp .env.example .env.local
npm install
npm run dev
```

Set `NEXT_PUBLIC_GENLAYER_CONTRACT_ADDRESS` to the address of the deployed
`WeatherParametricInsurance` contract.

`NEXT_PUBLIC_GENLAYER_NETWORK` supports:
- `studionet`
- `testnetAsimov`
- `testnetBradbury`

The dashboard reads policy state from the deployed contract and uses GenLayerJS
for wallet-signed writes, receipt polling, consensus status handling, funding,
evaluation, settlement confirmation, and policy renewal.
