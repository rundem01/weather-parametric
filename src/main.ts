import "./style.css";
import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionStatus } from "genlayer-js/types";

interface EthereumProvider {
  request(args: {
    method: string;
    params?: unknown[];
  }): Promise<unknown>;
  on?: (event: string, handler: (...args: unknown[]) => void) => void;
}

declare global {
  interface Window {
    ethereum?: EthereumProvider;
  }
}

type ContractAddress = `0x${string}`;

const CONTRACT_ADDRESS = (import.meta.env.VITE_GENLAYER_CONTRACT_ADDRESS || "") as ContractAddress | "";
const NETWORK = import.meta.env.VITE_GENLAYER_NETWORK || "studionet";

const STUDIONET_CHAIN_ID = "0xf21f";

const STUDIONET_CHAIN = {
  chainId: STUDIONET_CHAIN_ID,
  chainName: "GenLayer Studionet",
  nativeCurrency: {
    name: "GEN",
    symbol: "GEN",
    decimals: 18,
  },
  rpcUrls: ["https://studio.genlayer.com/api"],
};

const CITY_FALLBACK = [
  "Cape Town, South Africa", "Johannesburg, South Africa", "Lagos, Nigeria",
  "Nairobi, Kenya", "Accra, Ghana", "Cairo, Egypt", "London, UK",
  "Paris, France", "Berlin, Germany", "Rome, Italy", "Madrid, Spain",
  "New York, USA", "Toronto, Canada", "Los Angeles, USA", "Mexico City, Mexico",
  "São Paulo, Brazil", "Buenos Aires, Argentina", "Lima, Peru", "Tokyo, Japan",
  "Osaka, Japan", "Seoul, South Korea", "Beijing, China", "Shanghai, China",
  "Singapore", "Hong Kong", "Bangkok, Thailand", "Mumbai, India", "Delhi, India",
  "Dubai, UAE", "Doha, Qatar", "Istanbul, Türkiye", "Sydney, Australia",
  "Melbourne, Australia", "Auckland, New Zealand", "Zurich, Switzerland",
  "Amsterdam, Netherlands", "Stockholm, Sweden", "Vienna, Austria", "Oslo, Norway",
  "Copenhagen, Denmark", "Lisbon, Portugal", "Dublin, Ireland", "Brussels, Belgium",
];

const app = document.querySelector<HTMLDivElement>("#app")!;

app.innerHTML = `
  <header class="topbar">
    <a href="#" class="brand">
      <img src="/mochi.png" alt="Mochi" />
      <span><strong>GenLayer</strong><small>Weather Parametric Insurance</small></span>
    </a>
    <nav>
      <a href="#policy">Policy</a>
      <a href="#verification">Verification</a>
      <a href="/api/docs" target="_blank" rel="noopener">API Docs</a>
      <button id="connect-wallet" class="button secondary">Connect wallet</button>
    </nav>
  </header>

  <main class="shell">
    <section class="hero">
      <div>
        <div class="eyebrow"><span></span> LIVE GENLAYER DEMO · ${NETWORK}</div>
        <h1>Weather risk, <em>verified on-chain.</em></h1>
        <p>
          Configure a parametric weather policy, read the deployed Intelligent Contract,
          query the live weather source, and submit the evaluation through GenLayerJS.
        </p>
        <div class="hero-actions">
          <a class="button primary" href="#policy">Open policy console</a>
          <a class="button secondary" href="/api/docs" target="_blank" rel="noopener">Explore API</a>
        </div>
      </div>
      <div class="hero-mascot"><div class="mascot-ring"></div><img src="/mochi.png" alt="Mochi mascot" /></div>
    </section>

    <section id="policy" class="card policy-card">
      <div class="section-heading">
        <div><div class="eyebrow"><span></span> ON-CHAIN POLICY</div><h2>Read the deployed contract</h2></div>
        <span id="chain-status" class="status-badge">Not connected</span>
      </div>

      <div class="toolbar">
        <label><span>Contract address</span><input id="contract-address" value="${CONTRACT_ADDRESS}" placeholder="0x…" /></label>
        <button id="read-contract" class="button secondary">Read contract</button>
      </div>

      <div class="policy-grid">
        <div><span>Policy location</span><strong id="policy-location">—</strong></div>
        <div><span>Threshold</span><strong id="policy-threshold">—</strong></div>
        <div><span>Trusted source</span><strong id="policy-source">—</strong></div>
        <div><span>Policy status</span><strong id="policy-status">—</strong></div>
        <div><span>Coverage window</span><strong id="policy-coverage">—</strong></div>
        <div><span>Funding</span><strong id="policy-funding">—</strong></div>
      </div>
    </section>

    <section id="verification" class="card verification-card">
      <div class="section-heading">
        <div><div class="eyebrow"><span></span> REAL WRITE PATH</div><h2>Submit the weather evaluation</h2><p>The button below calls <code>evaluate_weather_trigger()</code> on the deployed GenLayer contract. It does not calculate the result locally.</p></div>
        <span id="tx-status" class="status-badge">Waiting</span>
      </div>

      <div class="policy-grid preview-grid">
        <div><span>Contract policy location</span><strong id="eval-location">—</strong></div>
        <div><span>Weather source sent to contract</span><strong id="eval-source">—</strong></div>
        <div><span>Browser weather preview</span><strong id="preview-temp">—</strong></div>
        <div><span>On-chain decision</span><strong id="onchain-decision">—</strong></div>
      </div>

      <div class="actions-row">
        <button id="test-weather" class="button secondary">Test live weather</button>
        <button id="evaluate-contract" class="button primary">Evaluate through GenLayer</button>
      </div>

      <div id="message" class="message">Connect the wallet that owns the deployed policy, then read the contract.</div>

      <div class="receipt" id="receipt">
        <div><span>Transaction</span><b id="tx-hash">—</b></div>
        <div><span>Execution</span><b id="tx-execution">—</b></div>
      </div>
    </section>

    <section class="card explorer-card">
      <div class="section-heading">
        <div><div class="eyebrow"><span></span> WEATHER EXPLORER</div><h2>Test cities independently</h2><p>This explorer tests the public weather adapter. The actual contract evaluation uses the contract's trusted source.</p></div>
      </div>
      <div class="toolbar">
        <label><span>City</span><select id="city"></select></label>
        <label><span>Comparison threshold</span><input id="preview-threshold" type="number" value="325" min="1" /></label>
        <button id="explore" class="button secondary">Check weather</button>
      </div>
      <div class="result-grid">
        <div class="result-card"><span>Temperature</span><strong id="weather-temp">—</strong><small id="weather-time">—</small></div>
        <div class="result-card"><span>Condition preview</span><strong id="weather-condition">—</strong><small>Browser preview only</small></div>
        <div class="result-card"><span>Source</span><strong id="weather-source">—</strong><small>Canonical API record</small></div>
      </div>
      <details class="raw"><summary>View API response</summary><pre id="raw-response">{}</pre></details>
    </section>

    <section class="card result-card-large">
      <div class="section-heading"><div><div class="eyebrow"><span></span> CONTRACT RESULT</div><h2>Latest on-chain state</h2></div></div>
      <div class="policy-grid">
        <div><span>Payout triggered</span><strong id="chain-payout">—</strong></div>
        <div><span>Consensus verified</span><strong id="chain-verified">—</strong></div>
        <div><span>Observed temperature</span><strong id="chain-observed">—</strong></div>
        <div><span>Observed at</span><strong id="chain-observed-at">—</strong></div>
        <div><span>Settlement status</span><strong id="chain-settlement">—</strong></div>
        <div><span>Paid out</span><strong id="chain-paid-out">—</strong></div>
        <div><span>Refunded</span><strong id="chain-refunded">—</strong></div>
        <div><span>Rejection reason</span><strong id="chain-invalid">—</strong></div>
      </div>
      <pre id="chain-summary">No state read yet.</pre>
    </section>
  </main>

  <footer><span>GenLayer Weather Parametric Insurance</span><span>Real wallet → real transaction → real contract state</span></footer>
`;

const $ = <T extends Element>(id: string) => document.getElementById(id) as unknown as T;
const connectButton = $<HTMLButtonElement>("connect-wallet");
const readButton = $<HTMLButtonElement>("read-contract");
const weatherTestButton = $<HTMLButtonElement>("test-weather");
const evaluateButton = $<HTMLButtonElement>("evaluate-contract");
const explorerButton = $<HTMLButtonElement>("explore");
const addressInput = $<HTMLInputElement>("contract-address");
const citySelect = $<HTMLSelectElement>("city");
const previewThreshold = $<HTMLInputElement>("preview-threshold");

let walletAddress = "";
let readClient = createClient({ chain: studionet });
let writeClient: ReturnType<typeof createClient> | null = null;
let policy: { location: string; threshold: number; source: string } | null = null;

const setStatus = (id: string, text: string, kind = "") => {
  const el = $<HTMLElement>(id);
  el.textContent = text;
  el.className = `status-badge ${kind}`.trim();
};

const setMessage = (text: string, kind = "") => {
  const el = $<HTMLElement>("message");
  el.textContent = text;
  el.className = `message ${kind}`.trim();
};

const tempText = (tenths: number | bigint) => `${Number(tenths) / 10}°C`;

function contractAddress(): ContractAddress {
  const value = addressInput.value.trim();
  if (!/^0x[a-fA-F0-9]{40}$/.test(value)) {
    throw new Error("Enter a valid deployed GenLayer contract address.");
  }
  return value as ContractAddress;
}

async function connectWallet() {
  const provider = window.ethereum;

  if (!provider) {
    throw new Error(
      "No injected wallet detected. Install or enable a browser wallet and try again."
    );
  }

  setStatus("chain-status", "Connecting", "loading");
  setMessage("Requesting access to your injected wallet…");

  const accounts = (await provider.request({
    method: "eth_requestAccounts",
  })) as string[];

  if (!accounts.length) {
    throw new Error("No wallet account was returned.");
  }

  walletAddress = accounts[0];

  let chainId = String(
    await provider.request({
      method: "eth_chainId",
    })
  ).toLowerCase();

  if (chainId !== STUDIONET_CHAIN_ID) {
    try {
      await provider.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: STUDIONET_CHAIN_ID }],
      });
    } catch (error: unknown) {
      const code = (error as { code?: number }).code;

      if (code === 4902) {
        await provider.request({
          method: "wallet_addEthereumChain",
          params: [STUDIONET_CHAIN],
        });

        await provider.request({
          method: "wallet_switchEthereumChain",
          params: [{ chainId: STUDIONET_CHAIN_ID }],
        });
      } else {
        throw new Error(
          "Your wallet could not switch to GenLayer Studionet. Switch to Studionet in your wallet and try again."
        );
      }
    }
  }

  chainId = String(
    await provider.request({
      method: "eth_chainId",
    })
  ).toLowerCase();

  if (chainId !== STUDIONET_CHAIN_ID) {
    throw new Error(
      `Wrong network (${chainId}). Connect the wallet to GenLayer Studionet (chain 61999).`
    );
  }

  writeClient = createClient({
    chain: studionet,
    account: walletAddress as ContractAddress,
    provider,
  });

  connectButton.textContent =
    `${walletAddress.slice(0, 6)}…${walletAddress.slice(-4)}`;

  setStatus("chain-status", "Wallet connected", "success");
  setMessage(
    "Wallet connected to GenLayer Studionet. Read the contract to load its policy.",
    "success"
  );
}

async function readContractState() {
  const address = contractAddress();
  setStatus("tx-status", "Reading", "loading");

  const read = (functionName: string) =>
    readClient.readContract({ address, functionName, args: [] });

  const [
    location, threshold, source, status, triggered, verified, observed, observedAt, summary,
    coverageStart, coverageEnd, invalidReason, settlementStatus,
    payoutAmount, paidOut, refunded, balance,
  ] = await Promise.all([
    read("get_location"),
    read("get_threshold_temp"),
    read("get_trusted_weather_source"),
    read("get_policy_status"),
    read("get_payout_triggered"),
    read("get_verified_by_consensus"),
    read("get_last_observed_temp"),
    read("get_last_observed_at"),
    read("get_weather_summary"),
    read("get_coverage_start"),
    read("get_coverage_end"),
    read("get_invalid_reason"),
    read("get_settlement_status"),
    read("get_payout_amount"),
    read("get_total_paid_out"),
    read("get_total_refunded"),
    read("get_contract_balance"),
  ]);

  policy = { location: String(location), threshold: Number(threshold), source: String(source) };
  $("policy-location").textContent = policy.location;
  $("policy-threshold").textContent = tempText(policy.threshold);
  $("policy-source").textContent = policy.source;
  $("policy-status").textContent = String(status);
  $("eval-location").textContent = policy.location;
  $("eval-source").textContent = policy.source;
  $("chain-payout").textContent = String(triggered) === "true" ? "TRIGGERED" : "NOT TRIGGERED";
  $("chain-verified").textContent = String(verified) === "true" ? "YES" : "NO";
  $("chain-observed").textContent = Number(observed) === 0 ? "—" : tempText(Number(observed));
  $("chain-observed-at").textContent = String(observedAt) || "—";
  $("chain-summary").textContent = String(summary || "No weather evaluation recorded yet.");

  $("policy-coverage").textContent = `${coverageStart} → ${coverageEnd}`;
  $("policy-funding").textContent =
    `${balance} / ${payoutAmount} GEN${Number(balance) >= Number(payoutAmount) ? " (funded)" : " (underfunded)"}`;
  $("chain-settlement").textContent = String(settlementStatus);
  $("chain-paid-out").textContent = `${paidOut} GEN`;
  $("chain-refunded").textContent = `${refunded} GEN`;
  $("chain-invalid").textContent = String(invalidReason) || "—";
  setStatus("tx-status", "State loaded", "success");
  setMessage("Read-only contract state loaded directly from GenLayer.", "success");
}

async function testTrustedWeatherSource() {
  if (!policy) await readContractState();
  if (!policy) throw new Error("Contract policy is not loaded.");

  setStatus("tx-status", "Testing source", "loading");
  const response = await fetch(policy.source, { cache: "no-store" });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Trusted weather source failed.");

  $("preview-temp").textContent = tempText(data.temperature_tenths_c);
  $("eval-source").textContent = policy.source;
  const triggered = Number(data.temperature_tenths_c) > policy.threshold;
  $("onchain-decision").textContent = triggered ? "Would trigger" : "Would not trigger";
  setStatus("tx-status", "Source reachable", "success");
  setMessage(`Trusted source returned ${tempText(data.temperature_tenths_c)} for ${data.location}.`, "success");

  return data;
}

async function evaluateOnChain() {
  const client = writeClient;
  if (!client) throw new Error("Connect the wallet first.");
  if (!policy) await readContractState();
  if (!policy) throw new Error("Contract policy is not loaded.");

  const address = contractAddress();
  if (walletAddress.toLowerCase() !== String(await readClient.readContract({ address, functionName: "get_policy_owner", args: [] })).toLowerCase()) {
    throw new Error("Connected wallet is not the policy owner. Use the wallet that deployed the policy.");
  }

  const response = await fetch(policy.source, { cache: "no-store" });
  const weather = await response.json();
  if (!response.ok) throw new Error(weather.detail || "Trusted weather source failed.");

  setStatus("tx-status", "Awaiting wallet", "loading");
  setMessage("Review the GenLayer transaction in your wallet and approve it.");

  const txHash = await client.writeContract({
    address,
    functionName: "evaluate_weather_trigger",
    args: [policy.source],
    value: BigInt(0),
  });

  $("tx-hash").textContent = String(txHash);
  setStatus("tx-status", "Consensus processing", "loading");
  setMessage("Transaction submitted. Waiting for GenLayer consensus and execution…", "success");

  const receipt = await readClient.waitForTransactionReceipt({
    hash: txHash,
    status: TransactionStatus.FINALIZED,
    interval: 5000,
    retries: 60,
  });

  // The receipt field name varies between node versions, so check each place
  // the execution result may appear before deciding anything failed.
  const anyReceipt = receipt as any;
  const executionRaw =
    anyReceipt?.txExecutionResultName ??
    anyReceipt?.tx_execution_result_name ??
    anyReceipt?.consensus_data?.leader_receipt?.execution_result ??
    "";

  const execution = String(executionRaw);
  $("tx-execution").textContent = execution || "FINISHED";

  // Only an explicit error counts as a failure. A missing or unrecognised
  // field means the transaction finalized without reporting a problem.
  if (execution === "FINISHED_WITH_ERROR" || execution === "ERROR") {
    setStatus("tx-status", "Execution failed", "error");
    throw new Error(`Transaction finalized but contract execution returned ${execution}.`);
  }

  setStatus("tx-status", "Finalized", "success");
  setMessage("GenLayer finalized the evaluation. Reading the updated contract state…", "success");
  await readContractState();

  // Explicitly show that the browser did not decide the final result.
  const chainTriggered = await readClient.readContract({
    address,
    functionName: "get_payout_triggered",
    args: [],
  });
  $("onchain-decision").textContent = String(chainTriggered) === "true" ? "TRIGGERED" : "NOT TRIGGERED";
  $("preview-temp").textContent = tempText(weather.temperature_tenths_c);
}

async function exploreWeather() {
  const city = encodeURIComponent(citySelect.value);
  const response = await fetch(`/api/weather?city=${city}`, { cache: "no-store" });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Weather request failed.");
  const limit = Number(previewThreshold.value);

  $("weather-temp").textContent = tempText(data.temperature_tenths_c);
  $("weather-time").textContent = `${data.location} · ${data.observed_at}`;
  $("weather-condition").textContent = Number(data.temperature_tenths_c) > limit ? "TRIGGERED" : "NOT TRIGGERED";
  $("weather-source").textContent = data.source || "Weather API";
  $("raw-response").textContent = JSON.stringify(data, null, 2);
}

async function loadCities() {
  const response = await fetch("/api/cities", { cache: "no-store" });
  if (!response.ok) throw new Error("Could not load global cities.");
  const data = await response.json();
  const cities = Array.isArray(data.cities) ? data.cities.map((c: { label: string }) => c.label) : CITY_FALLBACK;
  citySelect.innerHTML = cities.map((city: string) => `<option>${city.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</option>`).join("");
  citySelect.value = cities.includes("Cape Town, South Africa") ? "Cape Town, South Africa" : cities[0];
}

connectButton.addEventListener("click", () => connectWallet().catch((error: Error) => setMessage(error.message, "error")));
readButton.addEventListener("click", () => readContractState().catch((error: Error) => setMessage(error.message, "error")));
weatherTestButton.addEventListener("click", () => testTrustedWeatherSource().catch((error: Error) => setMessage(error.message, "error")));
evaluateButton.addEventListener("click", () => evaluateOnChain().catch((error: Error) => setMessage(error.message, "error")));
explorerButton.addEventListener("click", () => exploreWeather().catch((error: Error) => setMessage(error.message, "error")));

if (window.ethereum?.on) {
  window.ethereum.on("accountsChanged", (accounts: unknown) => {
    const nextAccounts = accounts as string[];

    if (!nextAccounts.length) {
      walletAddress = "";
      writeClient = null;
      connectButton.textContent = "Connect wallet";
      setStatus("chain-status", "Not connected");
      setMessage("Wallet disconnected.", "error");
      return;
    }

    walletAddress = nextAccounts[0];
    connectButton.textContent =
      `${walletAddress.slice(0, 6)}…${walletAddress.slice(-4)}`;
    writeClient = createClient({
      chain: studionet,
      account: walletAddress as ContractAddress,
      provider: window.ethereum,
    });

    setStatus("chain-status", "Account changed", "success");
    setMessage(
      "Wallet account changed. Read the contract again before submitting.",
      "success"
    );
  });

  window.ethereum.on("chainChanged", () => {
    writeClient = null;
    setStatus("chain-status", "Network changed", "error");
    setMessage(
      "Wallet network changed. Reconnect to GenLayer Studionet before submitting.",
      "error"
    );
  });
}

async function restoreWalletConnection() {
  const provider = window.ethereum;
  if (!provider) return;

  const accounts = (await provider.request({
    method: "eth_accounts",
  })) as string[];

  if (!accounts.length) return;

  const chainId = String(
    await provider.request({ method: "eth_chainId" })
  ).toLowerCase();

  if (chainId !== STUDIONET_CHAIN_ID) {
    setStatus("chain-status", "Wrong network", "error");
    setMessage(
      "Wallet is connected but not on GenLayer Studionet. Click Connect wallet to switch.",
      "error"
    );
    return;
  }

  walletAddress = accounts[0];
  writeClient = createClient({
    chain: studionet,
    account: walletAddress as ContractAddress,
    provider,
  });

  connectButton.textContent =
    `${walletAddress.slice(0, 6)}…${walletAddress.slice(-4)}`;
  setStatus("chain-status", "Wallet connected", "success");
}

restoreWalletConnection().catch(() => {
  setStatus("chain-status", "Not connected");
});

loadCities().catch(() => {
  citySelect.innerHTML = CITY_FALLBACK.map((city) => `<option>${city}</option>`).join("");
});
if (CONTRACT_ADDRESS) readContractState().catch(() => setMessage("Contract address is configured but could not be read yet. Connect to StudioNet and verify the address.", "error"));
