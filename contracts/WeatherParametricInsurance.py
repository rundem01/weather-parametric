# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from datetime import datetime, timezone
import json


class WeatherParametricInsurance(gl.Contract):
    """
    Weather parametric-insurance Intelligent Contract.

    Lifecycle
    ---------
    ACTIVE → evaluate_weather_trigger() → TRIGGERED / NOT_TRIGGERED / INVALID / EXPIRED
    TRIGGERED → confirm_settlement() → SETTLED
    SETTLED / NOT_TRIGGERED / INVALID / EXPIRED → renew_policy() → ACTIVE

    Weather-source schema (canonical — the /api/weather adapter MUST match this)
    ---------------------------------------------------------------------------
    {
        "location":             "Cape Town, South Africa",   # str
        "temperature_tenths_c": 325,                         # int  (325 = 32.5 °C)
        "observed_at":          "2026-08-22T12:00:00Z"       # ISO-8601 UTC str
    }

    temperature_tenths_c is an integer number of tenths of a degree Celsius.
    Valid range is −100 °C to +100 °C (−1000 to 1000 in tenths).

    Settlement note
    ---------------
    confirm_settlement() records that an eligible policy has been settled.
    It is a state primitive — it does not itself transfer GEN. A production
    deployment connects this state to a dedicated payout module or vault.
    """

    policy_owner: Address
    policyholder: Address

    location: str
    threshold_temp: i32          # tenths of a degree Celsius
    trusted_weather_source: str

    policy_start: u64
    policy_end: u64

    payout_amount: u256
    total_funded: u256

    policy_status: str           # ACTIVE | TRIGGERED | NOT_TRIGGERED | INVALID | EXPIRED | SETTLED
    settlement_status: str       # PENDING | ELIGIBLE | NOT_APPLICABLE | SETTLED | EXPIRED
    settlement_reference: str

    payout_triggered: bool
    verified_by_consensus: bool
    evaluation_count: u32

    last_observed_temp_tenths: i32
    last_observed_location: str
    last_observed_at: str
    last_weather_source: str
    weather_summary: str

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------

    def __init__(
        self,
        location: str,
        threshold_temp: i32,
        trusted_weather_source: str,
        policy_duration_days: u32,
        payout_amount: u256,
    ) -> None:
        if location == "":
            raise gl.vm.UserError("LOCATION_REQUIRED")

        if threshold_temp < -1000 or threshold_temp > 1000:
            raise gl.vm.UserError("THRESHOLD_OUT_OF_RANGE")

        if trusted_weather_source == "":
            raise gl.vm.UserError("WEATHER_SOURCE_REQUIRED")

        if policy_duration_days == 0:
            raise gl.vm.UserError("POLICY_DURATION_REQUIRED")

        if payout_amount == u256(0):
            raise gl.vm.UserError("PAYOUT_AMOUNT_REQUIRED")

        now = int(datetime.now(timezone.utc).timestamp())

        self.policy_owner = gl.message.sender_address
        self.policyholder = gl.message.sender_address

        self.location = location
        self.threshold_temp = threshold_temp
        self.trusted_weather_source = trusted_weather_source

        self.policy_start = u64(now)
        self.policy_end = u64(now + int(policy_duration_days) * 86400)

        self.payout_amount = payout_amount
        self.total_funded = u256(0)

        self.policy_status = "ACTIVE"
        self.settlement_status = "PENDING"
        self.settlement_reference = ""

        self.payout_triggered = False
        self.verified_by_consensus = False
        self.evaluation_count = u32(0)

        self.last_observed_temp_tenths = i32(0)
        self.last_observed_location = ""
        self.last_observed_at = ""
        self.last_weather_source = ""
        self.weather_summary = ""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_owner(self) -> None:
        if gl.message.sender_address != self.policy_owner:
            raise gl.vm.UserError("ONLY_OWNER")

    def _is_expired(self) -> bool:
        now = int(datetime.now(timezone.utc).timestamp())
        return now >= int(self.policy_end)

    # ------------------------------------------------------------------
    # Primary read interface
    # ------------------------------------------------------------------

    @gl.public.view
    def get_complete_storage(self) -> dict:
        """Return all contract state as a single dict.

        This is the canonical read method used by the GenLayer SDK and Studio.
        Individual getter methods are retained for ABI compatibility.
        """
        return {
            "policy_owner": str(self.policy_owner),
            "policyholder": str(self.policyholder),
            "location": self.location,
            "threshold_temp": int(self.threshold_temp),
            "trusted_weather_source": self.trusted_weather_source,
            "policy_start": int(self.policy_start),
            "policy_end": int(self.policy_end),
            "payout_amount": int(self.payout_amount),
            "total_funded": int(self.total_funded),
            "policy_status": self.policy_status,
            "settlement_status": self.settlement_status,
            "settlement_reference": self.settlement_reference,
            "payout_triggered": self.payout_triggered,
            "verified_by_consensus": self.verified_by_consensus,
            "evaluation_count": int(self.evaluation_count),
            "last_observed_temp_tenths": int(self.last_observed_temp_tenths),
            "last_observed_location": self.last_observed_location,
            "last_observed_at": self.last_observed_at,
            "last_weather_source": self.last_weather_source,
            "weather_summary": self.weather_summary,
        }

    # ------------------------------------------------------------------
    # Individual getters (ABI compatibility)
    # ------------------------------------------------------------------

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
    def get_policy_status(self) -> str:
        return self.policy_status

    @gl.public.view
    def get_settlement_status(self) -> str:
        return self.settlement_status

    @gl.public.view
    def get_settlement_reference(self) -> str:
        return self.settlement_reference

    @gl.public.view
    def get_policy_start(self) -> u64:
        return self.policy_start

    @gl.public.view
    def get_policy_end(self) -> u64:
        return self.policy_end

    @gl.public.view
    def get_payout_amount(self) -> u256:
        return self.payout_amount

    @gl.public.view
    def get_total_funded(self) -> u256:
        return self.total_funded

    @gl.public.view
    def get_contract_balance(self) -> u256:
        return self.balance

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

    # ------------------------------------------------------------------
    # Funding
    # ------------------------------------------------------------------

    @gl.public.write.payable
    def fund_policy(self) -> None:
        """Accept GEN funding for this policy.

        Funding is accepted while ACTIVE or TRIGGERED. If the policy has
        already triggered, additional funding still counts toward total_funded
        and satisfies the confirm_settlement() funding check if the balance
        was previously insufficient.
        """
        if self.policy_status not in ("ACTIVE", "TRIGGERED"):
            raise gl.vm.UserError("POLICY_NOT_OPEN_FOR_FUNDING")

        amount = gl.message.value
        if amount == u256(0):
            raise gl.vm.UserError("NO_FUNDS_SENT")

        self.total_funded = self.total_funded + amount

    # ------------------------------------------------------------------
    # Weather evaluation
    # ------------------------------------------------------------------

    @gl.public.write
    def evaluate_weather_trigger(self, weather_api_url: str) -> None:
        """Fetch weather data from the trusted source and evaluate the policy.

        Uses GenLayer consensus (gl.vm.run_nondet) so every validator
        independently fetches and evaluates the weather response. The contract
        then independently re-verifies the threshold comparison.

        Steps
        -----
        1. Pre-flight guards (owner, expiry, status, URL trust policy).
        2. leader_fn  — fetch → normalise → LLM decision.
        3. validator_fn — independent fetch → LLM decision → compare to leader.
        4. Post-consensus deterministic re-verification.
        5. State commit.
        """
        self._require_owner()

        # Check expiry before checking status. A lapsed ACTIVE policy is marked
        # EXPIRED rather than passing the POLICY_NOT_ACTIVE guard silently.
        # Note: evaluate_weather_trigger cannot be called on a TRIGGERED policy
        # (the POLICY_NOT_ACTIVE guard below fires), so this path cannot
        # overwrite a valid trigger result.
        if self._is_expired():
            self.policy_status = "EXPIRED"
            self.settlement_status = "EXPIRED"
            self.payout_triggered = False
            self.weather_summary = "Policy expired before evaluation."
            raise gl.vm.UserError("POLICY_EXPIRED")

        if self.policy_status != "ACTIVE":
            raise gl.vm.UserError("POLICY_NOT_ACTIVE")

        if weather_api_url != self.trusted_weather_source:
            raise gl.vm.UserError("UNTRUSTED_WEATHER_SOURCE")

        # Capture all storage values as locals BEFORE entering any nondet closure.
        # Accessing `self` inside a nondet block is not supported — each validator
        # runs in its own sandbox without the contract's persistent state.
        _location = self.location
        _threshold_temp = int(self.threshold_temp)
        _weather_api_url = weather_api_url

        def _fetch_and_normalise(url: str) -> dict:
            """Fetch the weather source and return a normalised record dict.

            Returns {"valid": False, "error": "..."} on any invalid or
            malformed response so callers never see raw exceptions.
            """
            try:
                response = gl.nondet.web.get(url)
                payload = json.loads(response.body.decode("utf-8"))
            except Exception:
                return {"valid": False, "error": "FETCH_OR_PARSE_FAILED"}

            if not isinstance(payload, dict):
                return {"valid": False, "error": "INVALID_JSON_OBJECT"}

            source_location = payload.get("location")
            temperature_tenths = payload.get("temperature_tenths_c")
            observed_at = payload.get("observed_at")

            if not isinstance(source_location, str):
                return {"valid": False, "error": "MISSING_LOCATION"}

            if not isinstance(observed_at, str):
                return {"valid": False, "error": "MISSING_TIMESTAMP"}

            # Must be an integer — floats are rejected to prevent precision
            # ambiguity across validators during consensus comparison.
            if not isinstance(temperature_tenths, int):
                return {"valid": False, "error": "TEMPERATURE_MUST_BE_INTEGER_TENTHS"}

            if temperature_tenths < -1000 or temperature_tenths > 1000:
                return {"valid": False, "error": "TEMPERATURE_OUT_OF_RANGE"}

            return {
                "valid": True,
                "location": source_location,
                "temperature_tenths_c": temperature_tenths,
                "observed_at": observed_at,
            }

        def leader_fn() -> dict:
            record = _fetch_and_normalise(_weather_api_url)

            prompt = f"""You are validating a weather parametric-insurance policy.

Policy location:
{_location}

Policy threshold:
{_threshold_temp} tenths of a degree Celsius.

Weather record (fetched from the trusted source):
{json.dumps(record, sort_keys=True)}

Return JSON only — no other text, no markdown:
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
1. If the record has valid=false, return valid=false and triggered=false.
2. location_match is true ONLY if the source location exactly matches the policy location.
3. Copy temperature_tenths_c exactly from the source record — do not round or convert.
4. triggered is true ONLY when temperature_tenths_c is strictly greater than {_threshold_temp}.
5. Copy observed_location and observed_at exactly from the source record.
6. Write a one-sentence summary faithful to the source record.
"""
            result = gl.nondet.exec_prompt(prompt, response_format="json")
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

                # Validators independently fetch and evaluate — never trust the
                # leader's raw fetch. Re-derive from the source directly.
                own_record = _fetch_and_normalise(_weather_api_url)
                if not own_record.get("valid", False):
                    # Cannot confirm the leader without a valid own reading.
                    return False

                validator_prompt = f"""Validate this weather record for a parametric-insurance policy.

Policy location:
{_location}

Policy threshold:
{_threshold_temp} tenths of a degree Celsius.

Weather record (independently fetched):
{json.dumps(own_record, sort_keys=True)}

Return JSON only — no other text, no markdown:
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
2. location_match must be true ONLY for an exact location match.
3. triggered must be true ONLY when temperature_tenths_c is strictly greater than {_threshold_temp}.
4. Copy observed_location and observed_at exactly.
"""
                validator_data = gl.nondet.exec_prompt(
                    validator_prompt,
                    response_format="json",
                )
                if not isinstance(validator_data, dict):
                    return False

                required_keys = (
                    "valid",
                    "location_match",
                    "temperature_tenths_c",
                    "triggered",
                    "observed_location",
                    "observed_at",
                )
                for key in required_keys:
                    if key not in leader_data or key not in validator_data:
                        return False

                return (
                    bool(leader_data["valid"]) == bool(validator_data["valid"])
                    and bool(leader_data["location_match"]) == bool(validator_data["location_match"])
                    and int(leader_data["temperature_tenths_c"]) == int(validator_data["temperature_tenths_c"])
                    and bool(leader_data["triggered"]) == bool(validator_data["triggered"])
                    and str(leader_data["observed_location"]) == str(validator_data["observed_location"])
                    and str(leader_data["observed_at"]) == str(validator_data["observed_at"])
                )

            except Exception:
                return False

        # gl.vm.run_nondet is preferred over run_nondet_unsafe: it runs the
        # validator in a sandbox and handles validator crashes with sensible
        # defaults rather than propagating them to the calling transaction.
        result = gl.vm.run_nondet(leader_fn, validator_fn)

        if not isinstance(result, dict):
            raise gl.vm.UserError("CONSENSUS_INVALID_RESULT")

        # --- Post-consensus deterministic re-verification ---
        # Type-assert every field. Any missing or wrong-type field marks the
        # evaluation INVALID rather than raising an unhandled exception.
        valid = bool(result.get("valid", False))
        location_match = bool(result.get("location_match", False))
        temperature_tenths = int(result.get("temperature_tenths_c", 0))
        triggered = bool(result.get("triggered", False))
        observed_location = str(result.get("observed_location", ""))
        observed_at = str(result.get("observed_at", ""))
        summary = str(result.get("summary", ""))

        self.evaluation_count = self.evaluation_count + u32(1)
        self.verified_by_consensus = True

        # Re-derive trigger decision from the raw temperature value.
        # This deterministic check must agree with the consensus result.
        expected_trigger = temperature_tenths > _threshold_temp
        exact_location_match = observed_location == _location

        if (
            not valid
            or not location_match
            or not exact_location_match
            or triggered != expected_trigger
        ):
            # Consensus result conflicts with deterministic policy rules.
            self.payout_triggered = False
            self.policy_status = "INVALID"
            self.settlement_status = "NOT_APPLICABLE"
            self.last_observed_temp_tenths = i32(temperature_tenths)
            self.last_observed_location = observed_location
            self.last_observed_at = observed_at
            self.last_weather_source = self.trusted_weather_source
            self.weather_summary = (
                summary if summary != ""
                else "Consensus result failed policy validation."
            )
            return

        # All checks passed — commit the consensus result.
        self.last_observed_temp_tenths = i32(temperature_tenths)
        self.last_observed_location = observed_location
        self.last_observed_at = observed_at
        self.last_weather_source = self.trusted_weather_source
        self.weather_summary = summary
        self.payout_triggered = expected_trigger

        if expected_trigger:
            self.policy_status = "TRIGGERED"
            self.settlement_status = "ELIGIBLE"
        else:
            self.policy_status = "NOT_TRIGGERED"
            self.settlement_status = "NOT_APPLICABLE"

    # ------------------------------------------------------------------
    # Settlement confirmation
    # ------------------------------------------------------------------

    @gl.public.write
    def confirm_settlement(self, settlement_reference: str) -> None:
        """Record that an eligible policy has been settled.

        Pre-conditions
        --------------
        - Caller must be the policy owner.
        - Policy status must be TRIGGERED.
        - Settlement status must be ELIGIBLE.
        - total_funded must be >= payout_amount.
        - settlement_reference must be a non-empty string (e.g. a tx hash
          from an external payout module or vault contract).
        """
        self._require_owner()

        if self.policy_status != "TRIGGERED":
            raise gl.vm.UserError("POLICY_NOT_TRIGGERED")

        if self.settlement_status != "ELIGIBLE":
            raise gl.vm.UserError("SETTLEMENT_NOT_ELIGIBLE")

        if self.total_funded < self.payout_amount:
            raise gl.vm.UserError("INSUFFICIENT_POLICY_FUNDS")

        if settlement_reference == "":
            raise gl.vm.UserError("SETTLEMENT_REFERENCE_REQUIRED")

        self.settlement_reference = settlement_reference
        self.settlement_status = "SETTLED"
        self.policy_status = "SETTLED"

    # ------------------------------------------------------------------
    # Policy renewal
    # ------------------------------------------------------------------

    @gl.public.write
    def renew_policy(
        self,
        new_location: str,
        new_threshold_temp: i32,
        new_trusted_weather_source: str,
        new_policy_duration_days: u32,
        new_payout_amount: u256,
    ) -> None:
        """Reset the policy to ACTIVE with a new configuration.

        Can only be called once the previous term has concluded
        (SETTLED, NOT_TRIGGERED, INVALID, or EXPIRED).

        Note on total_funded: the balance carries over from the prior term,
        enabling a pre-funded renewal without a separate fund_policy call.
        To start with a zero balance, deploy a fresh contract instead.
        """
        self._require_owner()

        if self.policy_status in ("ACTIVE", "TRIGGERED"):
            raise gl.vm.UserError("POLICY_STILL_ACTIVE")

        if new_location == "":
            raise gl.vm.UserError("LOCATION_REQUIRED")

        if new_threshold_temp < -1000 or new_threshold_temp > 1000:
            raise gl.vm.UserError("THRESHOLD_OUT_OF_RANGE")

        if new_trusted_weather_source == "":
            raise gl.vm.UserError("WEATHER_SOURCE_REQUIRED")

        if new_policy_duration_days == 0:
            raise gl.vm.UserError("POLICY_DURATION_REQUIRED")

        if new_payout_amount == u256(0):
            raise gl.vm.UserError("PAYOUT_AMOUNT_REQUIRED")

        now = int(datetime.now(timezone.utc).timestamp())

        self.location = new_location
        self.threshold_temp = new_threshold_temp
        self.trusted_weather_source = new_trusted_weather_source

        self.policy_start = u64(now)
        self.policy_end = u64(now + int(new_policy_duration_days) * 86400)

        self.payout_amount = new_payout_amount

        self.policy_status = "ACTIVE"
        self.settlement_status = "PENDING"
        self.settlement_reference = ""

        self.payout_triggered = False
        self.verified_by_consensus = False
        self.evaluation_count = u32(0)

        self.last_observed_temp_tenths = i32(0)
        self.last_observed_location = ""
        self.last_observed_at = ""
        self.last_weather_source = ""
        self.weather_summary = ""
