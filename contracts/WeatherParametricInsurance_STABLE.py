# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from datetime import datetime, timezone
import json


class WeatherParametricInsurance(gl.Contract):
    """
    Weather parametric-insurance primitive.

    Expected weather-source JSON:
    {
        "location": "Cape Town, South Africa",
        "temperature_tenths_c": 325,
        "observed_at": "2026-08-22T12:00:00Z"
    }

    325 means 32.5°C.
    """

    policy_owner: Address
    policyholder: Address

    location: str
    threshold_temp: i32
    trusted_weather_source: str

    policy_start: u64
    policy_end: u64

    payout_amount: u256
    total_funded: u256

    policy_status: str
    settlement_status: str
    settlement_reference: str

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
    ):
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
        self.policy_end = u64(
            now + (int(policy_duration_days) * 86400)
        )

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

    # =========================================================
    # Internal helpers
    # =========================================================

    def _require_owner(self) -> None:
        if gl.message.sender_address != self.policy_owner:
            raise gl.vm.UserError("ONLY_OWNER")

    def _is_expired(self) -> bool:
        now = int(datetime.now(timezone.utc).timestamp())
        return now >= int(self.policy_end)

    # =========================================================
    # Read methods
    # =========================================================

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

    # =========================================================
    # Funding
    # =========================================================

    @gl.public.write.payable
    def fund_policy(self) -> None:
        if self.policy_status not in ("ACTIVE", "TRIGGERED"):
            raise gl.vm.UserError("POLICY_NOT_OPEN_FOR_FUNDING")

        amount = gl.message.value

        if amount == u256(0):
            raise gl.vm.UserError("NO_FUNDS_SENT")

        self.total_funded = self.total_funded + amount

    # =========================================================
    # Weather evaluation
    # =========================================================

    @gl.public.write
    def evaluate_weather_trigger(self, weather_api_url: str) -> None:
        self._require_owner()

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

        def fetch_weather_record():
            response = gl.nondet.web.get(weather_api_url)
            payload = json.loads(response.body.decode("utf-8"))

            if not isinstance(payload, dict):
                return {
                    "valid": False,
                    "error": "INVALID_JSON_OBJECT",
                }

            source_location = payload.get("location")
            temperature_tenths = payload.get(
                "temperature_tenths_c"
            )
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

        def leader_fn():
            record = fetch_weather_record()

            prompt = f"""
You are validating a weather parametric-insurance policy.

Policy location:
{self.location}

Policy threshold:
{self.threshold_temp} tenths of a degree Celsius.

Weather record:
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
1. If valid is false in the source record, return valid=false and triggered=false.
2. location_match is true only if the source location exactly matches
   the policy location.
3. Copy temperature_tenths_c exactly from the source record.
4. triggered is true only when temperature_tenths_c is strictly greater
   than the policy threshold.
5. Copy observed_location and observed_at exactly from the source record.
6. Keep the summary faithful to the source record.
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
Validate this normalized weather record for the same policy.

Policy location:
{self.location}

Policy threshold:
{self.threshold_temp} tenths of a degree Celsius.

Weather record:
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
2. location_match must be true only for an exact location match.
3. triggered must be true only when temperature_tenths_c
   is strictly greater than the policy threshold.
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
                    if key not in leader_data:
                        return False
                    if key not in validator_data:
                        return False

                return (
                    bool(leader_data["valid"])
                    == bool(validator_data["valid"])
                    and bool(leader_data["location_match"])
                    == bool(validator_data["location_match"])
                    and int(leader_data["temperature_tenths_c"])
                    == int(validator_data["temperature_tenths_c"])
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

        if not isinstance(result, dict):
            raise gl.vm.UserError("CONSENSUS_INVALID_RESULT")

        self.evaluation_count = (
            self.evaluation_count + u32(1)
        )
        self.verified_by_consensus = True

        valid = bool(result.get("valid", False))
        location_match = bool(
            result.get("location_match", False)
        )
        temperature_tenths = int(
            result.get("temperature_tenths_c", 0)
        )
        triggered = bool(
            result.get("triggered", False)
        )

        observed_location = str(
            result.get("observed_location", "")
        )
        observed_at = str(
            result.get("observed_at", "")
        )
        summary = str(
            result.get("summary", "")
        )

        expected_trigger = (
            temperature_tenths > int(self.threshold_temp)
        )

        exact_location_match = (
            observed_location == self.location
        )

        # Consensus result must agree with deterministic policy rules.
        if (
            not valid
            or not location_match
            or not exact_location_match
            or triggered != expected_trigger
        ):
            self.payout_triggered = False
            self.policy_status = "INVALID"
            self.settlement_status = "NOT_APPLICABLE"
            self.last_observed_temp_tenths = i32(
                temperature_tenths
            )
            self.last_observed_location = observed_location
            self.last_observed_at = observed_at
            self.last_weather_source = (
                self.trusted_weather_source
            )
            self.weather_summary = (
                summary
                if summary != ""
                else "Consensus result failed policy validation."
            )
            return

        self.last_observed_temp_tenths = i32(
            temperature_tenths
        )
        self.last_observed_location = observed_location
        self.last_observed_at = observed_at
        self.last_weather_source = (
            self.trusted_weather_source
        )
        self.weather_summary = summary

        self.payout_triggered = expected_trigger

        if expected_trigger:
            self.policy_status = "TRIGGERED"
            self.settlement_status = "ELIGIBLE"
        else:
            self.policy_status = "NOT_TRIGGERED"
            self.settlement_status = "NOT_APPLICABLE"

    # =========================================================
    # Settlement confirmation
    # =========================================================

    @gl.public.write
    def confirm_settlement(
        self,
        settlement_reference: str,
    ) -> None:
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

    # =========================================================
    # Policy renewal
    # =========================================================

    @gl.public.write
    def renew_policy(
        self,
        new_location: str,
        new_threshold_temp: i32,
        new_trusted_weather_source: str,
        new_policy_duration_days: u32,
        new_payout_amount: u256,
    ) -> None:
        self._require_owner()

        if self.policy_status in ("ACTIVE", "TRIGGERED"):
            raise gl.vm.UserError("POLICY_STILL_ACTIVE")

        if new_location == "":
            raise gl.vm.UserError("LOCATION_REQUIRED")

        if (
            new_threshold_temp < -1000
            or new_threshold_temp > 1000
        ):
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
        self.trusted_weather_source = (
            new_trusted_weather_source
        )

        self.policy_start = u64(now)
        self.policy_end = u64(
            now + (int(new_policy_duration_days) * 86400)
        )

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
