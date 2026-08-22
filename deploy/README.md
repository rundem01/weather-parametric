# Deployment

Use GenLayer Studio for the first deployment.

1. Open `contracts/WeatherParametricInsurance.py`.
2. Confirm Studio loads the schema and exposes the five constructor fields.
3. Use the values in `deployment_inputs.json` (replace the trusted endpoint).
4. Deploy and copy the contract address.
5. Put the address in `frontend/.env.local`.
6. Run the frontend and connect the same owner wallet.

For local/CI deployment, use the current GenLayer CLI/deployment workflow from
the official documentation rather than checking credentials into the project.

## Trusted weather source

After deploying the frontend publicly, use the deployed app's URL as the trusted
source. For the first policy, the source format is:

`https://YOUR-DOMAIN/api/weather?city=Cape%20Town%2C%20South%20Africa`

Because the contract uses an exact-URL trust policy, do not substitute a different
URL at evaluation time.
