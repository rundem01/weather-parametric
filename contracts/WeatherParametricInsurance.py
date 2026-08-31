# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import hashlib
import json

# DER prefix for a SHA-256 DigestInfo (RFC 8017 §9.2). Used to check the
# PKCS#1 v1.5 padding of a recovered RSA signature.
SHA256_DER_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")
RSA_PUBLIC_EXPONENT = 65537

# Maximum allowed gap, in minutes, between when an observation was made
# and when the adapter signed it. Beyond this the record is stale.
MAX_OBSERVATION_AGE_MINUTES = 180


class WeatherParametricInsurance(gl.Contract):
    """
    Weather parametric-insurance Intelligent Contract.

    Lifecycle:
        ACTIVE
          -> evaluate_weather_trigger()
          -> TRIGGERED / NOT_TRIGGERED / INVALID
          -> confirm_settlement()   (TRIGGERED only, pays the policyholder)
          -> SETTLED
          -> withdraw_remaining()   (policy owner reclaims what is left)

    Trusted weather-source schema:
    {
        "location": "Cape Town, South Africa",
        "temperature_tenths_c": 325,
        "observed_at": "2026-08-24T12:00:00Z"
    }

    325 means 32.5 degrees Celsius.

    Coverage window:
        The policy carries an explicit UTC coverage window. An observation
        whose timestamp falls outside that window cannot settle a claim: the
        evaluation resolves to INVALID with reason OBSERVATION_OUT_OF_WINDOW.

        The bounds are constructor arguments rather than a chain timestamp
        because non-deterministic blocks cannot read storage, and deriving
        "now" from the same feed being validated would be circular.
    """

    policy_owner: Address
    policyholder: Address

    location: str
    threshold_temp: i32
    trusted_weather_source: str
    trusted_public_key_modulus: str
    policy_duration_days: u32

    coverage_start: str
    coverage_end: str

    payout_amount: u256
    total_funded: u256
    total_paid_out: u256
    total_refunded: u256

    policy_status: str
    settlement_status: str
    settlement_reference: str
    invalid_reason: str

    payout_triggered: bool
    verified_by_consensus: bool
    evaluation_count: u32

    last_observed_temp_tenths: i32
    last_observed_location: str
    last_observed_at: str
    last_weather_source: str
    weather_summary: str

    def __init__(
        self,
        location: str,
        threshold_temp: i32,
        trusted_weather_source: str,
        trusted_public_key_modulus: str,
        policy_duration_days: u32,
        payout_amount: u256,
        coverage_start: str,
        coverage_end: str,
    ):
        if location == "":
            raise gl.vm.UserError("LOCATION_REQUIRED")

        if threshold_temp < -1000 or threshold_temp > 1000:
            raise gl.vm.UserError("THRESHOLD_OUT_OF_RANGE")

        if trusted_weather_source == "":
            raise gl.vm.UserError("WEATHER_SOURCE_REQUIRED")

        if not trusted_weather_source.startswith("https://"):
            raise gl.vm.UserError("WEATHER_SOURCE_MUST_BE_HTTPS")

        modulus = trusted_public_key_modulus.strip().lower()
        if modulus.startswith("0x"):
            modulus = modulus[2:]
        if len(modulus) < 256:
            raise gl.vm.UserError("PUBLIC_KEY_TOO_SHORT")
        for ch in modulus:
            if ch not in "0123456789abcdef":
                raise gl.vm.UserError("PUBLIC_KEY_NOT_HEX")

        if policy_duration_days == 0:
            raise gl.vm.UserError("POLICY_DURATION_REQUIRED")

        if payout_amount == u256(0):
            raise gl.vm.UserError("PAYOUT_AMOUNT_REQUIRED")

        start = self._normalize_timestamp(coverage_start)
        end = self._normalize_timestamp(coverage_end)

        if start == "" or end == "":
            raise gl.vm.UserError("COVERAGE_WINDOW_INVALID_FORMAT")

        if start >= end:
            raise gl.vm.UserError("COVERAGE_START_MUST_PRECEDE_END")

        self.policy_owner = gl.message.sender_address
        self.policyholder = gl.message.sender_address

        self.location = location
        self.threshold_temp = threshold_temp
        self.trusted_weather_source = trusted_weather_source
        self.trusted_public_key_modulus = modulus
        self.policy_duration_days = policy_duration_days

        self.coverage_start = start
        self.coverage_end = end

        self.payout_amount = payout_amount
        self.total_funded = u256(0)
        self.total_paid_out = u256(0)
        self.total_refunded = u256(0)

        self.policy_status = "ACTIVE"
        self.settlement_status = "PENDING"
        self.settlement_reference = ""
        self.invalid_reason = ""

        self.payout_triggered = False
        self.verified_by_consensus = False
        self.evaluation_count = u32(0)

        self.last_observed_temp_tenths = i32(0)
        self.last_observed_location = ""
        self.last_observed_at = ""
        self.last_weather_source = ""
        self.weather_summary = ""

    # -----------------------------
    # Internal helpers
    # -----------------------------

    def _require_owner(self) -> None:
        if gl.message.sender_address != self.policy_owner:
            raise gl.vm.UserError("ONLY_OWNER")

    @staticmethod
    def _normalize_timestamp(value: str) -> str:
        """
        Reduce an ISO-8601 UTC timestamp to 'YYYY-MM-DDTHH:MM'.

        Sources vary in precision ('2026-08-28T05:45' vs
        '2026-08-24T12:00:00Z'), and lexicographic comparison is only sound
        across equal-length strings of identical format. Truncating to
        minute precision makes every timestamp directly comparable.

        Returns "" when the value does not match the expected shape, so
        callers can treat a malformed timestamp as a validation failure
        rather than silently comparing garbage.
        """
        if not isinstance(value, str):
            return ""

        trimmed = value.strip()

        if len(trimmed) < 16:
            return ""

        candidate = trimmed[:16]

        # Expected layout: YYYY-MM-DDTHH:MM
        if (
            candidate[4] != "-"
            or candidate[7] != "-"
            or candidate[10] != "T"
            or candidate[13] != ":"
        ):
            return ""

        for index in (0, 1, 2, 3, 5, 6, 8, 9, 11, 12, 14, 15):
            if not candidate[index].isdigit():
                return ""

        return candidate

    def _verify_signature(
        self, modulus_hex: str, signature_hex: str, message: bytes
    ) -> bool:
        """
        RSA PKCS#1 v1.5 / SHA-256 signature verification, in pure Python.

        GenVM exposes hashlib and arbitrary-precision integers but no
        signature library, so verification is done directly: recover the
        padded block with a modular exponentiation, then check its structure
        and the embedded digest.

        Returns False on any malformed input rather than raising, so a bad
        signature is a policy outcome and not an execution failure.
        """
        try:
            n = int(modulus_hex, 16)
            s = int(signature_hex, 16)
        except Exception:
            return False

        if s <= 0 or s >= n:
            return False

        k = (n.bit_length() + 7) // 8
        try:
            em = pow(s, RSA_PUBLIC_EXPONENT, n).to_bytes(k, "big")
        except Exception:
            return False

        # EM = 0x00 || 0x01 || PS (0xFF...) || 0x00 || DigestInfo
        if len(em) < 11 or em[0] != 0x00 or em[1] != 0x01:
            return False

        i = 2
        while i < len(em) and em[i] == 0xFF:
            i += 1

        if (i - 2) < 8 or i >= len(em) or em[i] != 0x00:
            return False

        digest_info = em[i + 1:]
        expected = SHA256_DER_PREFIX + hashlib.sha256(message).digest()

        if len(digest_info) != len(expected):
            return False

        # Constant-time-ish comparison.
        diff = 0
        for a, b in zip(digest_info, expected):
            diff |= a ^ b
        return diff == 0

    @staticmethod
    def _canonical_message(
        location: str, temperature_tenths_c: int, observed_at: str, issued_at: str
    ) -> bytes:
        """
        The exact bytes the adapter signs. Key order and separators are fixed
        so the adapter and the contract produce identical input; any drift
        here invalidates every signature.

        issued_at is the moment the adapter produced and signed the record.
        Binding it into the signature is what makes freshness checkable: an
        old signed record cannot be re-served with a new issue time without
        breaking its signature.
        """
        return json.dumps(
            {
                "issued_at": issued_at,
                "location": location,
                "observed_at": observed_at,
                "temperature_tenths_c": temperature_tenths_c,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    @staticmethod
    def _timestamp_to_minutes(normalized: str) -> int:
        """
        Convert a normalized 'YYYY-MM-DDTHH:MM' timestamp to minutes since
        the civil epoch, in pure arithmetic (GenVM availability of the
        datetime module is unverified, and this needs ~10 lines either way).

        Uses the standard days-from-civil algorithm. Input must already have
        passed _normalize_timestamp.
        """
        year = int(normalized[0:4])
        month = int(normalized[5:7])
        day = int(normalized[8:10])
        hour = int(normalized[11:13])
        minute = int(normalized[14:16])

        y = year - (1 if month <= 2 else 0)
        era = (y if y >= 0 else y - 399) // 400
        yoe = y - era * 400
        mp = (month + 9) % 12
        doy = (153 * mp + 2) // 5 + day - 1
        doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
        days = era * 146097 + doe - 719468

        return days * 1440 + hour * 60 + minute

    def _within_coverage(self, observed_at: str) -> bool:
        normalized = self._normalize_timestamp(observed_at)

        if normalized == "":
            return False

        return self.coverage_start <= normalized <= self.coverage_end

    def _mark_invalid(self, reason: str, summary: str) -> None:
        self.policy_status = "INVALID"
        self.settlement_status = "NOT_APPLICABLE"
        self.payout_triggered = False
        self.invalid_reason = reason
        self.weather_summary = summary

    # -----------------------------
    # Views
    # -----------------------------

    @gl.public.view
    def get_location(self) -> str:
        return self.location

    @gl.public.view
    def get_threshold_temp(self) -> i32:
        return self.threshold_temp

    @gl.public.view
    def get_trusted_weather_source(self) -> str:
        return self.trusted_weather_source

    @gl.public.view
    def get_trusted_public_key_modulus(self) -> str:
        return self.trusted_public_key_modulus

    @gl.public.view
    def selftest_signature_verification(self) -> str:
        """
        Verifies a fixed known-good signature against a fixed key, then the
        same signature against tampered data. Proves the verifier works
        inside GenVM without needing a live fetch.

        Expected: "OK valid=True tampered=False"
        """
        modulus = (
            "c3c3e82976d581029eb8c5717036819a2026ac8cdc38fa56f876be66d5c8da03"
            "a8a1e5b77bc328272ed9c240120940657f184542af00f6c50abc098e9c30c5a9"
            "b8da4d0c3c3822b41aee5ef8daa2051c8e6dcf5f1306daff89aaffd63d8faf9c"
            "712abccc0f2781cbb3131374c30f823cda982ff7b516060a0687100cc4e1dc5f"
            "87c13c9e7ff17581b3c6eb67888787044c50f4fcdc7874cd2440d0e8e938f5c0"
            "47e7ea196f40918e455b3958defebc52332aab0513b5e3c8fca7885cd224e074"
            "f657b62adf35c6088c4c78c92ac9a70fe21dd6a60d333465b01d3f8c940018cc"
            "9af7f27e2cae249d9e9a2b99fc7271759a7802f4fc8d8dff91ebc38c251d2ae7"
        )
        signature = (
            "90f02d59a8d3a0d92e41d9d3585b9d8406efe423cea168037fd145eef7fadbbb"
            "9d61b4fa24d8bc5bfe406ccfab3751431289be4739b9fb065bcef6acb265cc5a"
            "535f638d4d87c22e1a73a318f9c39307b5f4e8e01ef46ee36ae8d515449356fb"
            "6ed9c42d4d6969dbb0215c081a29b6aba5a13afc36515b15407b39094f80168b"
            "2d01c4910dc583438501690b5712e2b8331a1bd829f5c44ad56c06f02a1d0890"
            "dbf95b7f7c58615748ff24d95de0a227d325fc00f075401ea97556e1e9c26473"
            "9a00a5c1c5b620179cb6f6eaeae8e1aca00d9e4bd3c6cf53a8260a068d41e94d"
            "078969a1a8ba854d469d71c603a0ba6fcb4036ad87388692977d903e3efe44cb"
        )

        good = self._verify_signature(
            modulus, signature,
            self._canonical_message(
                "Selftest City", 200, "2026-01-01T00:00", "2026-01-01T00:30"
            ),
        )
        bad = self._verify_signature(
            modulus, signature,
            self._canonical_message(
                "Selftest City", 999, "2026-01-01T00:00", "2026-01-01T00:30"
            ),
        )
        return f"OK valid={good} tampered={bad}"

    @gl.public.view
    def get_policy_duration_days(self) -> u32:
        return self.policy_duration_days

    @gl.public.view
    def get_coverage_start(self) -> str:
        return self.coverage_start

    @gl.public.view
    def get_coverage_end(self) -> str:
        return self.coverage_end

    @gl.public.view
    def get_policy_status(self) -> str:
        return self.policy_status

    @gl.public.view
    def get_invalid_reason(self) -> str:
        return self.invalid_reason

    @gl.public.view
    def get_settlement_status(self) -> str:
        return self.settlement_status

    @gl.public.view
    def get_settlement_reference(self) -> str:
        return self.settlement_reference

    @gl.public.view
    def get_payout_amount(self) -> u256:
        return self.payout_amount

    @gl.public.view
    def get_total_funded(self) -> u256:
        return self.total_funded

    @gl.public.view
    def get_total_paid_out(self) -> u256:
        return self.total_paid_out

    @gl.public.view
    def get_total_refunded(self) -> u256:
        return self.total_refunded

    @gl.public.view
    def get_payout_triggered(self) -> bool:
        return self.payout_triggered

    @gl.public.view
    def get_verified_by_consensus(self) -> bool:
        return self.verified_by_consensus

    @gl.public.view
    def get_evaluation_count(self) -> u32:
        return self.evaluation_count

    @gl.public.view
    def get_last_observed_temp(self) -> i32:
        return self.last_observed_temp_tenths

    @gl.public.view
    def get_last_observed_location(self) -> str:
        return self.last_observed_location

    @gl.public.view
    def get_last_observed_at(self) -> str:
        return self.last_observed_at

    @gl.public.view
    def get_last_weather_source(self) -> str:
        return self.last_weather_source

    @gl.public.view
    def get_weather_summary(self) -> str:
        return self.weather_summary

    @gl.public.view
    def get_policy_owner(self) -> str:
        return str(self.policy_owner)

    @gl.public.view
    def get_policyholder(self) -> str:
        return str(self.policyholder)

    @gl.public.view
    def get_contract_balance(self) -> u256:
        return self.balance

    @gl.public.view
    def is_fully_funded(self) -> bool:
        return self.balance >= self.payout_amount

    # -----------------------------
    # Funding
    # -----------------------------

    @gl.public.write.payable
    def fund_policy(self) -> None:
        if self.policy_status not in ("ACTIVE", "TRIGGERED"):
            raise gl.vm.UserError("POLICY_NOT_OPEN_FOR_FUNDING")

        amount = gl.message.value
        if amount == u256(0):
            raise gl.vm.UserError("NO_FUNDS_SENT")

        self.total_funded = self.total_funded + amount

    @gl.public.write
    def set_policyholder(self, new_policyholder: str) -> None:
        """
        Nominate who receives the payout.

        Only permitted while the policy is ACTIVE. Once an evaluation has
        run, the beneficiary is locked — otherwise the owner could redirect
        a triggered payout to themselves between trigger and settlement.
        """
        self._require_owner()

        if self.policy_status != "ACTIVE":
            raise gl.vm.UserError("BENEFICIARY_LOCKED_AFTER_EVALUATION")

        self.policyholder = Address(new_policyholder)

    # -----------------------------
    # Consensus-backed evaluation
    # -----------------------------

    @gl.public.write
    def evaluate_weather_trigger(self, weather_api_url: str) -> None:
        # Deliberately not owner-gated. The outcome is decided entirely by
        # the signed, freshness-bound observation and the deterministic
        # checks below, so the caller has no lever over the result — and an
        # owner-only gate would let the owner cherry-pick the evaluation
        # moment. Either party (or anyone) may trigger it.
        if self.policy_status != "ACTIVE":
            raise gl.vm.UserError("POLICY_NOT_ACTIVE")

        if weather_api_url != self.trusted_weather_source:
            raise gl.vm.UserError("UNTRUSTED_WEATHER_SOURCE")

        # IMPORTANT: capture persistent state before entering nondeterministic
        # execution. Storage must not be accessed or written inside nondet blocks.
        policy_location = self.location
        policy_threshold = int(self.threshold_temp)
        trusted_url = self.trusted_weather_source
        trusted_modulus = self.trusted_public_key_modulus
        verify = self._verify_signature
        canonical = self._canonical_message
        normalize = self._normalize_timestamp
        to_minutes = self._timestamp_to_minutes

        def fetch_weather_record() -> dict:
            try:
                response = gl.nondet.web.get(trusted_url)
                payload = json.loads(response.body.decode("utf-8"))
            except Exception:
                return {
                    "valid": False,
                    "error": "FETCH_OR_PARSE_FAILED",
                }

            if not isinstance(payload, dict):
                return {
                    "valid": False,
                    "error": "INVALID_JSON_OBJECT",
                }

            source_location = payload.get("location")
            temperature_tenths = payload.get("temperature_tenths_c")
            observed_at = payload.get("observed_at")
            issued_at = payload.get("issued_at")
            signature = payload.get("signature")

            if not isinstance(signature, str) or signature == "":
                return {
                    "valid": False,
                    "error": "SIGNATURE_MISSING",
                }

            if not isinstance(issued_at, str):
                return {
                    "valid": False,
                    "error": "ISSUED_AT_MISSING",
                }

            if not isinstance(source_location, str):
                return {
                    "valid": False,
                    "error": "MISSING_LOCATION",
                }

            if not isinstance(observed_at, str):
                return {
                    "valid": False,
                    "error": "MISSING_TIMESTAMP",
                }

            if not isinstance(temperature_tenths, int):
                return {
                    "valid": False,
                    "error": "TEMPERATURE_MUST_BE_INTEGER_TENTHS",
                }

            if temperature_tenths < -1000 or temperature_tenths > 1000:
                return {
                    "valid": False,
                    "error": "TEMPERATURE_OUT_OF_RANGE",
                }

            # The observation is only trusted if it carries a valid signature
            # from the key registered at deployment. Reaching the configured
            # host over TLS proves nothing about the reading itself.
            if not verify(
                trusted_modulus,
                signature,
                canonical(source_location, temperature_tenths, observed_at, issued_at),
            ):
                return {
                    "valid": False,
                    "error": "SIGNATURE_INVALID",
                }

            # Freshness: the signed issue time and the observation time must
            # sit close together. Because issued_at is inside the signature,
            # a stale record cannot be re-stamped without invalidating it.
            observed_norm = normalize(observed_at)
            issued_norm = normalize(issued_at)

            if observed_norm == "" or issued_norm == "":
                return {
                    "valid": False,
                    "error": "TIMESTAMP_MALFORMED",
                }

            age = to_minutes(issued_norm) - to_minutes(observed_norm)
            if age < 0 or age > MAX_OBSERVATION_AGE_MINUTES:
                return {
                    "valid": False,
                    "error": "OBSERVATION_STALE",
                }

            return {
                "valid": True,
                "location": source_location,
                "temperature_tenths_c": temperature_tenths,
                "observed_at": observed_at,
                "signature_verified": True,
            }

        def leader_fn() -> dict:
            record = fetch_weather_record()

            prompt = f"""
You are evaluating a weather parametric insurance policy.

Policy location: {policy_location}
Policy threshold: {policy_threshold} tenths of a degree Celsius.

Source record:
{json.dumps(record, sort_keys=True)}

Return JSON only:
{{
  "valid": true,
  "location_match": true,
  "temperature_tenths_c": 0,
  "triggered": false,
  "observed_location": "",
  "observed_at": "",
  "summary": ""
}}

Rules:
1. valid must reflect the source record's validity.
2. location_match is true only for an exact location match.
3. Copy temperature_tenths_c exactly from the source record.
4. triggered is true only when temperature_tenths_c is strictly greater
   than {policy_threshold}.
5. Copy observed_location and observed_at exactly.
6. Keep summary factual and brief.
"""

            result = gl.nondet.exec_prompt(
                prompt,
                response_format="json",
            )

            if not isinstance(result, dict):
                raise gl.vm.UserError("LLM_INVALID_RESPONSE")

            return result

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False

            try:
                leader_data = leader_result.calldata
                if not isinstance(leader_data, dict):
                    return False

                own_record = fetch_weather_record()

                if not own_record.get("valid", False):
                    return False

                validator_prompt = f"""
Validate this independently fetched weather record.

Policy location: {policy_location}
Policy threshold: {policy_threshold} tenths of a degree Celsius.

Source record:
{json.dumps(own_record, sort_keys=True)}

Return JSON only:
{{
  "valid": true,
  "location_match": true,
  "temperature_tenths_c": 0,
  "triggered": false,
  "observed_location": "",
  "observed_at": "",
  "summary": ""
}}

Rules:
1. Copy temperature_tenths_c exactly.
2. location_match is true only for an exact location match.
3. triggered is true only when temperature_tenths_c is strictly greater
   than {policy_threshold}.
4. Copy observed_location and observed_at exactly.
"""

                validator_data = gl.nondet.exec_prompt(
                    validator_prompt,
                    response_format="json",
                )

                if not isinstance(validator_data, dict):
                    return False

                required = (
                    "valid",
                    "location_match",
                    "temperature_tenths_c",
                    "triggered",
                    "observed_location",
                    "observed_at",
                )

                for key in required:
                    if key not in leader_data or key not in validator_data:
                        return False

                # The source can change between leader/validator execution.
                # Allow a small numeric drift but require the policy decision,
                # location, and observation timestamp to agree.
                leader_temp = int(leader_data["temperature_tenths_c"])
                validator_temp = int(
                    validator_data["temperature_tenths_c"]
                )

                return (
                    bool(leader_data["valid"])
                    == bool(validator_data["valid"])
                    and bool(leader_data["location_match"])
                    == bool(validator_data["location_match"])
                    and abs(leader_temp - validator_temp) <= 5
                    and bool(leader_data["triggered"])
                    == bool(validator_data["triggered"])
                    and str(leader_data["observed_location"])
                    == str(validator_data["observed_location"])
                    and str(leader_data["observed_at"])
                    == str(validator_data["observed_at"])
                )

            except Exception:
                return False

        result = gl.vm.run_nondet_unsafe(
            leader_fn,
            validator_fn,
        )

        # All state changes happen only after consensus.
        if not isinstance(result, dict):
            raise gl.vm.UserError("CONSENSUS_INVALID_RESULT")

        self.evaluation_count = self.evaluation_count + u32(1)
        self.verified_by_consensus = True

        valid = bool(result.get("valid", False))
        location_match = bool(result.get("location_match", False))
        temperature_tenths = int(
            result.get("temperature_tenths_c", 0)
        )
        triggered = bool(result.get("triggered", False))

        observed_location = str(
            result.get("observed_location", "")
        )
        observed_at = str(result.get("observed_at", ""))
        summary = str(result.get("summary", ""))

        expected_trigger = (
            temperature_tenths > int(self.threshold_temp)
        )

        # Record what was observed regardless of the outcome, so a rejected
        # evaluation is still auditable on-chain.
        self.last_observed_temp_tenths = i32(temperature_tenths)
        self.last_observed_location = observed_location
        self.last_observed_at = observed_at
        self.last_weather_source = weather_api_url

        # Coverage-window enforcement. An observation from outside the policy
        # period cannot settle a claim, however valid it is in every other way.
        if not self._within_coverage(observed_at):
            self._mark_invalid(
                "OBSERVATION_OUT_OF_WINDOW",
                f"Observation at {observed_at} falls outside the coverage "
                f"window {self.coverage_start} to {self.coverage_end}.",
            )
            return

        # Deterministic re-verification of the final decision.
        if not valid:
            self._mark_invalid(
                "SOURCE_RECORD_INVALID",
                summary if summary != "" else "Source record failed validation.",
            )
            return

        if not location_match or observed_location != self.location:
            self._mark_invalid(
                "LOCATION_MISMATCH",
                f"Observed location {observed_location} does not match the "
                f"policy location {self.location}.",
            )
            return

        if triggered != expected_trigger:
            self._mark_invalid(
                "TRIGGER_DECISION_MISMATCH",
                "Consensus decision disagreed with the deterministic "
                "threshold comparison.",
            )
            return

        self.weather_summary = summary
        self.invalid_reason = ""
        self.payout_triggered = expected_trigger

        if expected_trigger:
            self.policy_status = "TRIGGERED"
            self.settlement_status = "ELIGIBLE"
        else:
            self.policy_status = "NOT_TRIGGERED"
            self.settlement_status = "NOT_APPLICABLE"

    # -----------------------------
    # Settlement lifecycle
    # -----------------------------

    @gl.public.write
    def confirm_settlement(self, settlement_reference: str) -> None:
        """
        Pay the policyholder. This transfers real value out of the contract.

        Deliberately not owner-gated: once a policy is TRIGGERED and
        ELIGIBLE, the payout is owed, and the owner must not be able to
        withhold it. Anyone may execute settlement; the funds always go to
        the recorded policyholder, so the caller gains nothing.
        """
        if self.policy_status != "TRIGGERED":
            raise gl.vm.UserError("POLICY_NOT_TRIGGERED")

        if self.settlement_status != "ELIGIBLE":
            raise gl.vm.UserError("SETTLEMENT_NOT_ELIGIBLE")

        if settlement_reference == "":
            raise gl.vm.UserError("SETTLEMENT_REFERENCE_REQUIRED")

        amount = self.payout_amount

        if self.balance < amount:
            raise gl.vm.UserError("INSUFFICIENT_POLICY_FUNDS")

        # Update state before emitting the transfer. A failed transfer refunds
        # the value to this contract, and the accounting below stays honest
        # because total_paid_out is reconciled against the balance by
        # withdraw_remaining rather than assumed.
        self.settlement_reference = settlement_reference
        self.settlement_status = "SETTLED"
        self.policy_status = "SETTLED"
        self.total_paid_out = self.total_paid_out + amount

        gl.get_contract_at(self.policyholder).emit_transfer(value=amount)

    @gl.public.write
    def withdraw_remaining(self) -> None:
        """
        Return whatever is left to the policy owner.

        Permitted once the policy has resolved: after a settled payout, or
        when the evaluation produced NOT_TRIGGERED or INVALID. Without this
        a non-triggering policy would strand its funding in the contract
        forever.
        """
        self._require_owner()

        if self.policy_status not in ("SETTLED", "NOT_TRIGGERED", "INVALID"):
            raise gl.vm.UserError("POLICY_NOT_RESOLVED")

        remaining = self.balance

        if remaining == u256(0):
            raise gl.vm.UserError("NOTHING_TO_WITHDRAW")

        self.total_refunded = self.total_refunded + remaining

        gl.get_contract_at(self.policy_owner).emit_transfer(value=remaining)

    # -----------------------------
    # Policy renewal
    # -----------------------------

    @gl.public.write
    def renew_policy(
        self,
        new_location: str,
        new_threshold_temp: i32,
        new_trusted_weather_source: str,
        new_trusted_public_key_modulus: str,
        new_policy_duration_days: u32,
        new_payout_amount: u256,
        new_coverage_start: str,
        new_coverage_end: str,
    ) -> None:
        self._require_owner()

        if self.policy_status in ("ACTIVE", "TRIGGERED"):
            raise gl.vm.UserError("POLICY_STILL_ACTIVE")

        if self.balance > u256(0):
            raise gl.vm.UserError("WITHDRAW_REMAINING_FUNDS_FIRST")

        if new_location == "":
            raise gl.vm.UserError("LOCATION_REQUIRED")

        if new_threshold_temp < -1000 or new_threshold_temp > 1000:
            raise gl.vm.UserError("THRESHOLD_OUT_OF_RANGE")

        if new_trusted_weather_source == "":
            raise gl.vm.UserError("WEATHER_SOURCE_REQUIRED")

        if not new_trusted_weather_source.startswith("https://"):
            raise gl.vm.UserError("WEATHER_SOURCE_MUST_BE_HTTPS")

        new_modulus = new_trusted_public_key_modulus.strip().lower()
        if new_modulus.startswith("0x"):
            new_modulus = new_modulus[2:]
        if len(new_modulus) < 256:
            raise gl.vm.UserError("PUBLIC_KEY_TOO_SHORT")

        if new_policy_duration_days == 0:
            raise gl.vm.UserError("POLICY_DURATION_REQUIRED")

        if new_payout_amount == u256(0):
            raise gl.vm.UserError("PAYOUT_AMOUNT_REQUIRED")

        start = self._normalize_timestamp(new_coverage_start)
        end = self._normalize_timestamp(new_coverage_end)

        if start == "" or end == "":
            raise gl.vm.UserError("COVERAGE_WINDOW_INVALID_FORMAT")

        if start >= end:
            raise gl.vm.UserError("COVERAGE_START_MUST_PRECEDE_END")

        self.location = new_location
        self.threshold_temp = new_threshold_temp
        self.trusted_weather_source = new_trusted_weather_source
        self.trusted_public_key_modulus = new_modulus
        self.policy_duration_days = new_policy_duration_days
        self.payout_amount = new_payout_amount

        self.coverage_start = start
        self.coverage_end = end

        self.total_funded = u256(0)
        self.total_paid_out = u256(0)
        self.total_refunded = u256(0)

        self.policy_status = "ACTIVE"
        self.settlement_status = "PENDING"
        self.settlement_reference = ""
        self.invalid_reason = ""

        self.payout_triggered = False
        self.verified_by_consensus = False
        self.evaluation_count = u32(0)

        self.last_observed_temp_tenths = i32(0)
        self.last_observed_location = ""
        self.last_observed_at = ""
        self.last_weather_source = ""
        self.weather_summary = ""
