from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Weather Parametric Insurance — API</title>
<style>
  :root {
    --bg: #f6f5fb; --card: #ffffff; --ink: #1b1b2f; --muted: #6b6b85;
    --accent: #7c3aed; --mono-bg: #14142b; --mono-ink: #e8e6ff;
    --border: #e4e2f0; --ok: #0f766e; --warn: #b45309;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }
  .wrap { max-width: 880px; margin: 0 auto; padding: 48px 24px 96px; }
  h1 { font-size: 1.9rem; margin: 0 0 4px; }
  .sub { color: var(--muted); margin: 0 0 40px; }
  h2 { font-size: 1.25rem; margin: 48px 0 12px; }
  h3 { font-size: 1rem; margin: 28px 0 8px; }
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 24px 28px; margin: 16px 0;
  }
  .method {
    display: inline-block; background: var(--accent); color: #fff;
    border-radius: 6px; padding: 2px 10px; font-weight: 600;
    font-size: .8rem; margin-right: 10px; vertical-align: 2px;
  }
  .path { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 1.05rem; }
  pre {
    background: var(--mono-bg); color: var(--mono-ink); border-radius: 10px;
    padding: 16px 18px; overflow-x: auto; font-size: .86rem; line-height: 1.55;
  }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  p code, li code, td code {
    background: #edeaf7; border-radius: 4px; padding: 1px 5px; font-size: .88em;
  }
  table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: .92rem; }
  th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }
  th { color: var(--muted); font-weight: 600; font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; }
  .muted { color: var(--muted); }
  .pill { display: inline-block; border: 1px solid var(--border); border-radius: 999px;
          padding: 1px 10px; font-size: .78rem; color: var(--muted); margin-left: 8px; }
  a { color: var(--accent); }
</style>
</head>
<body>
<div class="wrap">

<h1>Weather Parametric Insurance API</h1>
<p class="sub">Trusted, signed weather-data adapter for the GenLayer Intelligent Contract.</p>

<div class="card">
<p>This service resolves a city through Open-Meteo and returns a canonical
observation record, <strong>cryptographically signed</strong> so the on-chain
policy can verify both its origin and its freshness. Validators inside GenLayer
consensus fetch this API independently; the contract accepts a reading only if
its signature verifies against the public key registered at deployment and its
timestamps sit within the freshness bound.</p>
</div>

<h2><span class="method">GET</span><span class="path">/api/weather</span></h2>
<div class="card">
<h3>Query parameters</h3>
<table>
<tr><th>Name</th><th>Type</th><th>Description</th></tr>
<tr><td><code>city</code></td><td>string, required</td>
<td>City label, e.g. <code>Cape Town, South Africa</code>. 2–100 characters.
Must match a supported label from <code>/api/cities</code>.</td></tr>
</table>

<h3>Response</h3>
<pre>{
  "location": "Cape Town, South Africa",
  "temperature_tenths_c": 135,
  "observed_at": "2026-08-31T13:45",
  "issued_at": "2026-08-31T13:47",
  "source": "Open-Meteo via Weather Parametric Insurance API",
  "signature": "8f3a1c…512 hex chars…",
  "signature_alg": "RSA-PKCS1v15-SHA256"
}</pre>

<table>
<tr><th>Field</th><th>Meaning</th></tr>
<tr><td><code>temperature_tenths_c</code></td>
<td>Integer tenths of a degree Celsius — <code>135</code> means 13.5&nbsp;°C.
Integers avoid floating-point disagreement between validators.</td></tr>
<tr><td><code>observed_at</code></td>
<td>When the reading was taken. UTC, minute precision,
<code>YYYY-MM-DDTHH:MM</code>.</td></tr>
<tr><td><code>issued_at</code></td>
<td>When this record was produced and signed. Bound inside the signature, so a
stale record cannot be re-served with a fresh stamp.</td></tr>
<tr><td><code>signature</code></td>
<td>Hex-encoded RSA-2048 signature (PKCS#1 v1.5, SHA-256) over the canonical
message below.</td></tr>
</table>

<h3>Canonical signed message</h3>
<p>The signature covers exactly these four fields, serialized with sorted keys
and no whitespace. Any consumer verifying the signature must rebuild this byte
string identically:</p>
<pre>{"issued_at":"2026-08-31T13:47","location":"Cape Town, South Africa","observed_at":"2026-08-31T13:45","temperature_tenths_c":135}</pre>

<h3>Errors</h3>
<table>
<tr><th>Status</th><th>Cause</th></tr>
<tr><td><code>422</code></td><td>Missing or malformed <code>city</code> parameter.</td></tr>
<tr><td><code>503</code></td><td>The signing key is not configured on the server.</td></tr>
<tr><td><code>502</code></td><td>Upstream weather source unavailable.</td></tr>
</table>

<h3>Example</h3>
<pre>curl "https://weather-parametric-real.vercel.app/api/weather?city=Cape%20Town%2C%20South%20Africa"</pre>
</div>

<h2><span class="method">GET</span><span class="path">/api/cities</span></h2>
<div class="card">
<p>Lists every supported city label. Labels must be used verbatim in
<code>/api/weather</code> — the contract compares locations exactly.</p>
<h3>Response</h3>
<pre>{
  "count": 43,
  "cities": [
    { "label": "Cape Town, South Africa" },
    { "label": "Johannesburg, South Africa" },
    …
  ]
}</pre>
<h3>Example</h3>
<pre>curl "https://weather-parametric-real.vercel.app/api/cities"</pre>
</div>

<h2>How the contract consumes this API <span class="pill">read this before integrating</span></h2>
<div class="card">
<p>The deployed policy stores one trusted URL and one RSA public modulus. During
<code>evaluate_weather_trigger()</code>, every GenLayer validator independently
fetches the trusted URL and, before the reading is considered at all:</p>
<table>
<tr><th>Check</th><th>Failure reason recorded on-chain</th></tr>
<tr><td>A <code>signature</code> field is present</td><td><code>SIGNATURE_MISSING</code></td></tr>
<tr><td>An <code>issued_at</code> field is present</td><td><code>ISSUED_AT_MISSING</code></td></tr>
<tr><td>Signature verifies against the registered public key</td><td><code>SIGNATURE_INVALID</code></td></tr>
<tr><td>Timestamps match <code>YYYY-MM-DDTHH:MM</code></td><td><code>TIMESTAMP_MALFORMED</code></td></tr>
<tr><td><code>issued_at − observed_at</code> is between 0 and 180 minutes</td><td><code>OBSERVATION_STALE</code></td></tr>
<tr><td><code>observed_at</code> falls inside the policy's coverage window</td><td><code>OBSERVATION_OUT_OF_WINDOW</code></td></tr>
</table>
<p>Responses are served with <code>Cache-Control:&nbsp;no-store</code> so each
validator receives a live reading rather than a shared cached one.</p>
<p class="muted">A signature establishes provenance, not honesty: it proves the
record came from the holder of the registered key and was not altered in
transit. The operator of this adapter could still sign a false reading — in
production the signing key belongs with an independent data provider.</p>
</div>

<p class="muted">Weather Parametric Insurance · built on GenLayer Intelligent
Contracts · <a href="/">back to the app</a></p>

</div>
</body>
</html>"""


@app.get("/api/docs")
def docs() -> HTMLResponse:
    return HTMLResponse(content=PAGE, headers={"Cache-Control": "public, max-age=300"})
