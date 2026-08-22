"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  CONTRACT_ADDRESS,
  NETWORK,
  readPolicyState,
  sendContractWrite,
} from "../lib/genlayer";

declare global {
  interface Window {
    ethereum?: {
      request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
    };
  }
}

const CITIES = [
  "Amsterdam, Netherlands", "Auckland, New Zealand", "Bangkok, Thailand",
  "Beijing, China", "Berlin, Germany", "Bogotá, Colombia", "Boston, USA",
  "Buenos Aires, Argentina", "Cairo, Egypt", "Cape Town, South Africa",
  "Chicago, USA", "Copenhagen, Denmark", "Delhi, India", "Dubai, UAE",
  "Hong Kong", "Houston, USA", "Istanbul, Türkiye", "Jakarta, Indonesia",
  "Johannesburg, South Africa", "Kuala Lumpur, Malaysia", "Lagos, Nigeria",
  "Lima, Peru", "London, UK", "Los Angeles, USA", "Madrid, Spain",
  "Manila, Philippines", "Mexico City, Mexico", "Miami, USA", "Mumbai, India",
  "Nairobi, Kenya", "New York, USA", "Oslo, Norway", "Paris, France",
  "Rio de Janeiro, Brazil", "Rome, Italy", "San Francisco, USA",
  "Santiago, Chile", "São Paulo, Brazil", "Seoul, South Korea",
  "Shanghai, China", "Singapore", "Stockholm, Sweden", "Sydney, Australia",
  "Tokyo, Japan", "Toronto, Canada", "Vancouver, Canada", "Vienna, Austria",
  "Washington, DC, USA", "Zurich, Switzerland",
];

const weatherSourceForCity = (city: string) =>
  `${typeof window !== "undefined" ? window.location.origin : ""}/api/weather?city=${encodeURIComponent(city)}`;

interface PolicyState {
  location: string;
  thresholdTemp: number;
  trustedSource: string;
  policyEnd: number;
  policyStatus: string;
  settlementStatus: string;
  payoutAmount: bigint;
  totalFunded: bigint;
  contractBalance: bigint;
  payoutTriggered: boolean;
  verified: boolean;
  evaluationCount: number;
  lastTemp: number;
  lastObservedAt: string;
  summary: string;
  policyOwner: string;
}

const formatGen = (value: bigint) => {
  const whole = value / BigInt(10 ** 18);
  const fraction = value % BigInt(10 ** 18);
  return `${whole}.${fraction.toString().padStart(18, "0").slice(0, 4)} GEN`;
};

export default function Home() {
  const [wallet, setWallet] = useState("");
  const [policy, setPolicy] = useState<PolicyState | null>(null);
  const [weatherUrl, setWeatherUrl] = useState("");
  const [fundAmount, setFundAmount] = useState("0");
  const [settlementReference, setSettlementReference] = useState("");
  const [renewLocation, setRenewLocation] = useState("Cape Town, South Africa");
  const [renewThreshold, setRenewThreshold] = useState("325");
  const [renewSource, setRenewSource] = useState("");
  const [renewDuration, setRenewDuration] = useState("30");
  const [renewPayout, setRenewPayout] = useState("1");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const isOwner = useMemo(
    () => !!wallet && !!policy?.policyOwner && wallet.toLowerCase() === policy.policyOwner.toLowerCase(),
    [wallet, policy]
  );

  const loadPolicy = async () => {
    setError("");
    try {
      const next = await readPolicyState();
      setPolicy(next);
      setWeatherUrl(next.trustedSource);
      setRenewLocation(next.location);
      setRenewThreshold(String(next.thresholdTemp));
      setRenewSource(next.trustedSource);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to read the contract.");
    }
  };

  useEffect(() => {
    if (CONTRACT_ADDRESS) void loadPolicy();
  }, []);

  const connectWallet = async () => {
    if (!window.ethereum) {
      setError("No browser wallet was detected. Install a compatible EVM wallet first.");
      return;
    }

    try {
      const accounts = (await window.ethereum.request({
        method: "eth_requestAccounts",
      })) as string[];

      setWallet(accounts[0] || "");
      setMessage("Wallet connected.");
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Wallet connection failed.");
    }
  };

  const runWrite = async (
    e: FormEvent<HTMLFormElement>,
    functionName: string,
    args: readonly unknown[] = [],
    value = BigInt(0),
  ) => {
    e.preventDefault();

    if (!wallet) {
      setError("Connect the policy owner wallet before sending a transaction.");
      return;
    }

    setBusy(true);
    setError("");
    setMessage("Submitting transaction and waiting for GenLayer consensus...");

    try {
      await sendContractWrite(
        wallet as `0x${string}`,
        window.ethereum,
        functionName,
        args,
        value,
      );
      setMessage("Transaction accepted. Refreshing the policy state...");
      await loadPolicy();
      setMessage("Policy state updated successfully.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Transaction failed.");
    } finally {
      setBusy(false);
    }
  };

  const evaluate = (e: FormEvent<HTMLFormElement>) =>
    runWrite(e, "evaluate_weather_trigger", [weatherUrl]);

  const fund = (e: FormEvent<HTMLFormElement>) => {
    const amount = Number(fundAmount);
    if (!Number.isFinite(amount) || amount <= 0) {
      e.preventDefault();
      setError("Enter a positive GEN funding amount.");
      return;
    }

    const wei = BigInt(Math.round(amount * 1e6)) * BigInt(10 ** 12);
    void runWrite(e, "fund_policy", [], wei);
  };

  const settle = (e: FormEvent<HTMLFormElement>) =>
    runWrite(e, "confirm_settlement", [settlementReference]);

  const renew = (e: FormEvent<HTMLFormElement>) => {
    const duration = Number(renewDuration);
    const payout = Number(renewPayout);

    if (!Number.isInteger(duration) || duration <= 0) {
      e.preventDefault();
      setError("Policy duration must be a positive whole number of days.");
      return;
    }

    if (!Number.isFinite(payout) || payout <= 0) {
      e.preventDefault();
      setError("Payout amount must be greater than zero.");
      return;
    }

    const payoutWei = BigInt(Math.round(payout * 1e6)) * BigInt(10 ** 12);

    void runWrite(e, "renew_policy", [
      renewLocation,
      Number(renewThreshold),
      renewSource,
      duration,
      payoutWei,
    ]);
  };

  const thresholdDisplay = policy ? `${(policy.thresholdTemp / 10).toFixed(1)}°C` : "—";
  const lastTempDisplay = policy?.lastTemp ? `${(policy.lastTemp / 10).toFixed(1)}°C` : "—";
  const expiresDisplay = policy
    ? new Date(policy.policyEnd * 1000).toLocaleString()
    : "—";

  return (
    <main className="min-h-screen bg-[#07080a] text-white">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_50%_-10%,rgba(255,255,255,0.06),transparent_38%)]" />

      <div className="relative mx-auto max-w-6xl px-5 py-10 sm:px-8">
        <header className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_12px_rgba(52,211,153,0.8)]" />
              <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-400">
                GenLayer · {NETWORK}
              </span>
            </div>
            <h1 className="text-4xl font-semibold tracking-[-0.04em] sm:text-5xl">
              Weather Parametric Insurance
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-500 sm:text-base">
              Verify a predefined weather condition through GenLayer consensus,
              preserve the evidence on-chain, and move the policy through a clear
              evaluation and settlement lifecycle.
            </p>
          </div>

          <button
            onClick={connectWallet}
            className="rounded-xl border border-white/[0.1] bg-white/[0.045] px-4 py-3 text-sm font-semibold text-slate-200 transition hover:border-white/[0.2] hover:bg-white/[0.07]"
          >
            {wallet ? `${wallet.slice(0, 6)}…${wallet.slice(-4)}` : "Connect wallet"}
          </button>
        </header>

        {!CONTRACT_ADDRESS && (
          <div className="mb-6 rounded-2xl border border-amber-400/15 bg-amber-400/[0.04] p-4 text-sm text-amber-200">
            Set <code>NEXT_PUBLIC_GENLAYER_CONTRACT_ADDRESS</code> before using the dashboard.
          </div>
        )}

        {error && (
          <div className="mb-6 rounded-2xl border border-red-400/15 bg-red-400/[0.04] p-4 text-sm text-red-200">
            {error}
          </div>
        )}

        {message && (
          <div className="mb-6 rounded-2xl border border-emerald-400/10 bg-emerald-400/[0.04] p-4 text-sm text-emerald-200">
            {message}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
          <section className="rounded-3xl border border-white/[0.08] bg-[#101216]/90 shadow-[0_30px_100px_rgba(0,0,0,0.4)] backdrop-blur-2xl">
            <div className="border-b border-white/[0.07] px-6 py-5 sm:px-8">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-600">On-chain policy</p>
                  <h2 className="mt-1 text-xl font-semibold">Policy configuration</h2>
                </div>
                <span className="rounded-full border border-white/[0.07] px-3 py-1 text-xs text-slate-400">
                  {policy?.policyStatus || "Loading"}
                </span>
              </div>
            </div>

            <div className="grid gap-6 p-6 sm:grid-cols-2 sm:p-8">
              <div>
                <p className="text-xs text-slate-600">Insured location</p>
                <p className="mt-2 text-base font-medium text-slate-200">{policy?.location || "—"}</p>
              </div>
              <div>
                <p className="text-xs text-slate-600">Trigger threshold</p>
                <p className="mt-2 text-base font-medium text-slate-200">Above {thresholdDisplay}</p>
              </div>
              <div className="sm:col-span-2">
                <p className="text-xs text-slate-600">Trusted weather source</p>
                <p className="mt-2 break-all rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3 font-mono text-xs text-slate-400">
                  {policy?.trustedSource || "—"}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-600">Policy expiry</p>
                <p className="mt-2 text-sm text-slate-300">{expiresDisplay}</p>
              </div>
              <div>
                <p className="text-xs text-slate-600">Payout amount</p>
                <p className="mt-2 text-sm text-slate-300">{policy ? formatGen(policy.payoutAmount) : "—"}</p>
              </div>
            </div>
          </section>

          <section className="rounded-3xl border border-white/[0.08] bg-[#101216]/90 p-6 shadow-[0_30px_100px_rgba(0,0,0,0.35)] sm:p-8">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-600">Decision state</p>
            <div className="mt-4 grid grid-cols-2 gap-3">
              {[
                ["Verification", policy?.verified ? "Verified" : "Pending"],
                ["Trigger", policy?.payoutTriggered ? "Triggered" : "Not triggered"],
                ["Settlement", policy?.settlementStatus || "Pending"],
                ["Evaluations", String(policy?.evaluationCount ?? 0)],
              ].map(([label, value]) => (
                <div key={label} className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
                  <p className="text-[11px] text-slate-600">{label}</p>
                  <p className="mt-2 text-sm font-semibold text-slate-300">{value}</p>
                </div>
              ))}
            </div>

            <div className="mt-3 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
              <p className="text-[11px] text-slate-600">Last observed temperature</p>
              <p className="mt-2 text-2xl font-semibold tracking-tight text-white">{lastTempDisplay}</p>
              <p className="mt-1 text-xs text-slate-600">{policy?.lastObservedAt || "No evaluation yet"}</p>
            </div>
          </section>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <section className="rounded-3xl border border-white/[0.08] bg-[#101216]/90 p-6 sm:p-8">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-600">Weather verification</p>
            <h2 className="mt-2 text-xl font-semibold">Evaluate the policy</h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              The contract only accepts its configured trusted source. The source response is normalized, then checked through comparative GenLayer consensus.
            </p>

            <form onSubmit={evaluate} className="mt-6 space-y-4">
              <input
                value={weatherUrl}
                readOnly
                placeholder="Trusted source URL"
                className="h-12 w-full cursor-not-allowed rounded-xl border border-white/[0.08] bg-[#08090b] px-4 font-mono text-xs text-slate-500 outline-none"
              />
              <button
                type="submit"
                disabled={busy || !isOwner || !policy || policy.policyStatus !== "ACTIVE"}
                className="w-full rounded-xl bg-white px-4 py-3.5 text-sm font-semibold text-[#07080a] transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {busy ? "Waiting for consensus…" : "Evaluate weather condition"}
              </button>
            </form>
          </section>

          <section className="rounded-3xl border border-white/[0.08] bg-[#101216]/90 p-6 sm:p-8">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-600">Funding</p>
            <h2 className="mt-2 text-xl font-semibold">Fund the policy</h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              Funding is tracked on-chain so the policy can expose a real settlement readiness state.
            </p>
            <form onSubmit={fund} className="mt-6 flex gap-3">
              <input
                value={fundAmount}
                onChange={(e) => setFundAmount(e.target.value)}
                inputMode="decimal"
                placeholder="GEN amount"
                className="h-12 min-w-0 flex-1 rounded-xl border border-white/[0.08] bg-[#08090b] px-4 text-sm text-slate-300 outline-none focus:border-white/25"
              />
              <button
                type="submit"
                disabled={busy || !isOwner}
                className="rounded-xl border border-white/[0.1] bg-white/[0.04] px-5 text-sm font-semibold text-slate-200 transition hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-40"
              >
                Fund
              </button>
            </form>
            <div className="mt-4 flex justify-between text-xs text-slate-600">
              <span>Contract balance</span>
              <span className="text-slate-400">{policy ? formatGen(policy.contractBalance) : "—"}</span>
            </div>
          </section>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <section className="rounded-3xl border border-white/[0.08] bg-[#101216]/90 p-6 sm:p-8">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-600">Settlement</p>
            <h2 className="mt-2 text-xl font-semibold">Confirm settlement</h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              After the weather trigger is verified, record the settlement reference to move the policy from eligible to settled.
            </p>
            <form onSubmit={settle} className="mt-6 space-y-4">
              <input
                value={settlementReference}
                onChange={(e) => setSettlementReference(e.target.value)}
                placeholder="Settlement reference"
                className="h-12 w-full rounded-xl border border-white/[0.08] bg-[#08090b] px-4 font-mono text-sm text-slate-300 outline-none focus:border-white/25"
              />
              <button
                type="submit"
                disabled={busy || !isOwner || policy?.settlementStatus !== "ELIGIBLE"}
                className="w-full rounded-xl border border-emerald-400/20 bg-emerald-400/[0.06] px-4 py-3.5 text-sm font-semibold text-emerald-300 transition hover:bg-emerald-400/[0.1] disabled:cursor-not-allowed disabled:opacity-40"
              >
                Confirm settlement
              </button>
            </form>
          </section>

          <section className="rounded-3xl border border-white/[0.08] bg-[#101216]/90 p-6 sm:p-8">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-600">Policy renewal</p>
            <h2 className="mt-2 text-xl font-semibold">Reuse the primitive</h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              Once a policy reaches a closed state, the owner can renew it with a new city, trusted source, threshold, duration, and payout amount.
            </p>
            <form onSubmit={renew} className="mt-6 grid gap-3 sm:grid-cols-2">
              <select
                value={renewLocation}
                onChange={(e) => {
                  const city = e.target.value;
                  setRenewLocation(city);
                  setRenewSource(weatherSourceForCity(city));
                }}
                className="h-12 rounded-xl border border-white/[0.08] bg-[#08090b] px-4 text-sm text-slate-300 outline-none focus:border-white/25"
              >
                {CITIES.map((city) => <option key={city} value={city}>{city}</option>)}
              </select>
              <input
                value={renewThreshold}
                onChange={(e) => setRenewThreshold(e.target.value)}
                inputMode="numeric"
                placeholder="325 = 32.5°C"
                className="h-12 rounded-xl border border-white/[0.08] bg-[#08090b] px-4 text-sm text-slate-300 outline-none focus:border-white/25"
              />
              <input
                value={renewSource}
                onChange={(e) => setRenewSource(e.target.value)}
                placeholder="Trusted source URL"
                className="h-12 rounded-xl border border-white/[0.08] bg-[#08090b] px-4 text-xs text-slate-300 outline-none focus:border-white/25 sm:col-span-2"
              />
              <input
                value={renewDuration}
                onChange={(e) => setRenewDuration(e.target.value)}
                inputMode="numeric"
                placeholder="Duration in days"
                className="h-12 rounded-xl border border-white/[0.08] bg-[#08090b] px-4 text-sm text-slate-300 outline-none focus:border-white/25"
              />
              <input
                value={renewPayout}
                onChange={(e) => setRenewPayout(e.target.value)}
                inputMode="decimal"
                placeholder="Payout in GEN"
                className="h-12 rounded-xl border border-white/[0.08] bg-[#08090b] px-4 text-sm text-slate-300 outline-none focus:border-white/25"
              />
              <button
                type="submit"
                disabled={busy || !isOwner || (policy?.policyStatus !== "SETTLED" && policy?.policyStatus !== "NOT_TRIGGERED" && policy?.policyStatus !== "EXPIRED" && policy?.policyStatus !== "INVALID")}
                className="rounded-xl border border-white/[0.1] bg-white/[0.04] px-4 py-3.5 text-sm font-semibold text-slate-200 transition hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-40 sm:col-span-2"
              >
                Renew policy
              </button>
            </form>
          </section>
        </div>

        <section className="mt-6 rounded-3xl border border-white/[0.08] bg-[#101216]/90 p-6 sm:p-8">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-600">Evidence</p>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4 sm:col-span-2">
              <p className="text-xs text-slate-600">Consensus weather summary</p>
              <p className="mt-2 text-sm leading-6 text-slate-400">{policy?.summary || "No evaluation evidence recorded yet."}</p>
            </div>
            <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
              <p className="text-xs text-slate-600">Last source</p>
              <p className="mt-2 break-all font-mono text-xs text-slate-400">{policy?.trustedSource || "—"}</p>
            </div>
          </div>
        </section>

        <footer className="mt-8 text-center text-[11px] text-slate-700">
          Weather conditions are verified through GenLayer consensus. The settlement confirmation state records the policy lifecycle; it does not by itself represent a completed external payment.
        </footer>
      </div>
    </main>
  );
}
