import { createClient } from "genlayer-js";
import {
  studionet,
  testnetAsimov,
  testnetBradbury,
} from "genlayer-js/chains";
import { ExecutionResult, TransactionStatus } from "genlayer-js/types";

export type SupportedNetwork =
  | "studionet"
  | "testnetAsimov"
  | "testnetBradbury";

export const NETWORK: SupportedNetwork =
  (process.env.NEXT_PUBLIC_GENLAYER_NETWORK as SupportedNetwork) ||
  "studionet";

export const CONTRACT_ADDRESS =
  process.env.NEXT_PUBLIC_GENLAYER_CONTRACT_ADDRESS || "";

const chainMap = {
  studionet,
  testnetAsimov,
  testnetBradbury,
};

export function getReadClient() {
  return createClient({ chain: chainMap[NETWORK] });
}

export function getWriteClient(
  address: `0x${string}`,
  provider: unknown
) {
  return createClient({
    chain: chainMap[NETWORK],
    account: address,
    provider,
  });
}

export async function readPolicyState() {
  if (!CONTRACT_ADDRESS) {
    throw new Error("NEXT_PUBLIC_GENLAYER_CONTRACT_ADDRESS is not configured.");
  }

  const client = getReadClient();
  const address = CONTRACT_ADDRESS as `0x${string}`;

  const [
    location,
    threshold,
    trustedSource,
    policyEnd,
    policyStatus,
    settlementStatus,
    payoutAmount,
    totalFunded,
    contractBalance,
    payoutTriggered,
    verified,
    evaluationCount,
    lastTemp,
    lastObservedAt,
    summary,
    policyOwner,
  ] = await Promise.all([
    client.readContract({ address, functionName: "get_location", args: [] }),
    client.readContract({ address, functionName: "get_threshold_temp", args: [] }),
    client.readContract({
      address,
      functionName: "get_trusted_weather_source",
      args: [],
    }),
    client.readContract({ address, functionName: "get_policy_end", args: [] }),
    client.readContract({ address, functionName: "get_policy_status", args: [] }),
    client.readContract({
      address,
      functionName: "get_settlement_status",
      args: [],
    }),
    client.readContract({
      address,
      functionName: "get_payout_amount",
      args: [],
    }),
    client.readContract({
      address,
      functionName: "get_total_funded",
      args: [],
    }),
    client.readContract({
      address,
      functionName: "get_contract_balance",
      args: [],
    }),
    client.readContract({
      address,
      functionName: "get_payout_triggered",
      args: [],
    }),
    client.readContract({
      address,
      functionName: "get_verified_by_consensus",
      args: [],
    }),
    client.readContract({
      address,
      functionName: "get_evaluation_count",
      args: [],
    }),
    client.readContract({
      address,
      functionName: "get_last_observed_temp",
      args: [],
    }),
    client.readContract({
      address,
      functionName: "get_last_observed_at",
      args: [],
    }),
    client.readContract({
      address,
      functionName: "get_weather_summary",
      args: [],
    }),
    client.readContract({
      address,
      functionName: "get_policy_owner",
      args: [],
    }),
  ]);

  return {
    location: String(location),
    thresholdTemp: Number(threshold),
    trustedSource: String(trustedSource),
    policyEnd: Number(policyEnd),
    policyStatus: String(policyStatus),
    settlementStatus: String(settlementStatus),
    payoutAmount: BigInt(payoutAmount as bigint),
    totalFunded: BigInt(totalFunded as bigint),
    contractBalance: BigInt(contractBalance as bigint),
    payoutTriggered: Boolean(payoutTriggered),
    verified: Boolean(verified),
    evaluationCount: Number(evaluationCount),
    lastTemp: Number(lastTemp),
    lastObservedAt: String(lastObservedAt),
    summary: String(summary),
    policyOwner: String(policyOwner),
  };
}

export async function sendContractWrite(
  walletAddress: `0x${string}`,
  provider: unknown,
  functionName: string,
  args: readonly unknown[] = [],
  value = BigInt(0),
) {
  if (!CONTRACT_ADDRESS) {
    throw new Error("NEXT_PUBLIC_GENLAYER_CONTRACT_ADDRESS is not configured.");
  }

  const client = getWriteClient(walletAddress, provider);
  await client.connect(NETWORK);

  const hash = await client.writeContract({
    address: CONTRACT_ADDRESS as `0x${string}`,
    functionName,
    args: [...args],
    value,
  });

  const receipt = await client.waitForTransactionReceipt({
    hash,
    status: TransactionStatus.ACCEPTED,
    interval: 5000,
    retries: 60,
    fullTransaction: false,
  });

  if (receipt.txExecutionResultName === ExecutionResult.FINISHED_WITH_ERROR) {
    throw new Error("The GenLayer contract execution failed.");
  }

  return { hash, receipt };
}
