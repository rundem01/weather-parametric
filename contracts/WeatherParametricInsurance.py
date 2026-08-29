# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json


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
        Nominate who receives the payout. Only meaningful before settlement.
        """
        self._require_owner()

        if self.policy_status == "SETTLED":
            raise gl.vm.UserError("POLICY_ALREADY_SETTLED")

        self.policyholder = Address(new_policyholder)

    # -----------------------------
    # Consensus-backed evaluation
    # -----------------------------

    @gl.public.write
    def evaluate_weather_trigger(self, weather_api_url: str) -> None:
        self._require_owner()

        if self.policy_status != "ACTIVE":
            raise gl.vm.UserError("POLICY_NOT_ACTIVE")

        if weather_api_url != self.trusted_weather_source:
            raise gl.vm.UserError("UNTRUSTED_WEATHER_SOURCE")

        # IMPORTANT: capture persistent state before entering nondeterministic
        # execution. Storage must not be accessed or written inside nondet blocks.
        policy_location = self.location
        policy_threshold = int(self.threshold_temp)
        trusted_url = self.trusted_weather_source

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

            return {
                "valid": True,
                "location": source_location,
                "temperature_tenths_c": temperature_tenths,
                "observed_at": observed_at,
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
        """
        self._require_owner()

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
