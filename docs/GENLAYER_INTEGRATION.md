# GenLayerJS integration

The frontend uses two clients:
- read client: unsigned reads over public RPC, no wallet needed
- write client: wallet-backed transactions

The evaluation flow:

readContract() × 17
   ↓
policy terms, coverage window, settlement accounting
   ↓
writeContract()
   ↓
evaluate_weather_trigger(trusted_source)   ← any wallet, not just the owner
   ↓
waitForTransactionReceipt(FINALIZED)
   ↓
read execution result (field name varies by node version)
   ↓
readContract() again → on-chain outcome
