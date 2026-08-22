from contracts.WeatherParametricInsurance import WeatherParametricInsurance


def test_constructor_state():
    contract = WeatherParametricInsurance(
        "Cape Town, South Africa",
        325,
        "https://weather.example/policy/cape-town.json",
        30,
        1,
    )

    assert contract.location == "Cape Town, South Africa"
    assert contract.threshold_temp == 325
    assert contract.trusted_weather_source == "https://weather.example/policy/cape-town.json"
    assert contract.policy_status == "ACTIVE"
    assert contract.settlement_status == "PENDING"
    assert contract.payout_triggered is False
    assert contract.verified_by_consensus is False


def test_source_trust_policy():
    contract = WeatherParametricInsurance(
        "Cape Town, South Africa",
        325,
        "https://weather.example/policy/cape-town.json",
        30,
        1,
    )

    assert contract.get_trusted_weather_source() == "https://weather.example/policy/cape-town.json"
    assert contract.get_policy_status() == "ACTIVE"
