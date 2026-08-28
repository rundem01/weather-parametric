# GenLayerJS integration

The frontend uses two clients:

- read client: public RPC reads
- write client: wallet-backed writes

The evaluation flow is:

```text
readContract()
   ↓
read get_location/get_threshold_temp/get_trusted_weather_source
   ↓
wallet owner check
   ↓
writeContract()
   ↓
evaluate_weather_trigger(trusted_source)
   ↓
waitForTransactionReceipt(FINALIZED)
   ↓
check txExecutionResultName
   ↓
readContract() again
```

This is the important difference from the rejected submission: the final result is read from the deployed Intelligent Contract, not calculated only in the browser.

The current GenLayerJS documentation describes the same read/write/receipt pattern. citeturn557122search0turn557122search3
