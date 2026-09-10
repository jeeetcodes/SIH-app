from app.schemas.scan import ExtractedLabelData
from app.services.rules_engine import RulesEngine

engine = RulesEngine()


def _fields(**overrides) -> ExtractedLabelData:
    base = dict(
        mrp="Rs. 150.00 incl. of all taxes",
        net_quantity="500 g",
        manufacturer_details="Acme Foods Pvt Ltd, Plot 12, MIDC, Pune, Maharashtra 411019, India",
        date_of_packing="08/2026",
        country_of_origin="India",
        consumer_care="care@acmefoods.example | 9876543210",
        unit_sale_price="Rs. 0.30/g",
    )
    base.update(overrides)
    return ExtractedLabelData(**base)


def test_compliant_label_scores_100() -> None:
    status, score, violations = engine.evaluate(_fields())
    assert status == "COMPLIANT"
    assert score == 100
    assert violations == []


def test_missing_mrp_is_critical() -> None:
    status, _, violations = engine.evaluate(_fields(mrp=None))
    assert status == "NON_COMPLIANT"
    assert any(item.rule_id == "LM-PCR-6-1-e" for item in violations)


def test_mrp_without_inclusive_taxes_is_critical() -> None:
    _, _, violations = engine.evaluate(_fields(mrp="Rs. 99.00"))
    assert any("incl" in item.message.lower() for item in violations)


def test_invalid_net_quantity_unit_gms() -> None:
    _, _, violations = engine.evaluate(_fields(net_quantity="500 gms"))
    assert any(item.field_name == "net_quantity" and item.severity == "CRITICAL" for item in violations)


def test_lbs_unit_is_rejected() -> None:
    _, _, violations = engine.evaluate(_fields(net_quantity="1 lbs"))
    assert any(item.field_name == "net_quantity" for item in violations)


def test_missing_consumer_care_is_major() -> None:
    status, score, violations = engine.evaluate(_fields(consumer_care=None))
    assert status == "NON_COMPLIANT"
    assert score == 90
    assert any(item.rule_id == "LM-PCR-6-1-h" and item.severity == "MAJOR" for item in violations)


def test_consumer_care_requires_phone_or_email() -> None:
    _, _, violations = engine.evaluate(_fields(consumer_care="customer desk"))
    assert any(item.rule_id == "LM-PCR-6-1-h" and item.severity == "MAJOR" for item in violations)


def test_missing_consumer_care_email_is_major() -> None:
    status, score, violations = engine.evaluate(_fields(consumer_care="9876543210"))
    assert status == "NON_COMPLIANT"
    assert score == 90
    assert any("email" in item.message.lower() for item in violations)


def test_missing_packing_date_is_critical() -> None:
    _, _, violations = engine.evaluate(_fields(date_of_packing=None))
    assert any(item.rule_id == "LM-PCR-6-1-d" for item in violations)


def test_incomplete_manufacturer_address_is_critical() -> None:
    _, _, violations = engine.evaluate(_fields(manufacturer_details="BrandX"))
    assert any(item.rule_id == "LM-PCR-6-1-a" for item in violations)


def test_imported_missing_origin_is_warning() -> None:
    status, score, violations = engine.evaluate(
        _fields(
            country_of_origin=None,
            manufacturer_details="Imported by Acme Traders, Plot 9, Andheri, Mumbai 400053",
        )
    )
    assert status == "COMPLIANT"
    assert score == 95
    assert any(item.rule_id == "LM-PCR-6-1-aa" and item.severity == "WARNING" for item in violations)


def test_dynamic_score_uses_critical_major_and_warning_weights() -> None:
    status, score, violations = engine.evaluate(
        ExtractedLabelData(
            mrp=None,
            net_quantity=None,
            manufacturer_details="BrandX",
            date_of_packing="08/2026",
            country_of_origin=None,
            consumer_care=None,
            unit_sale_price=None,
        )
    )
    assert status == "NON_COMPLIANT"
    # 3 CRITICAL (MRP, qty, incomplete address) + 1 MAJOR (care) = 100 - 75 - 10
    assert score == 15
    assert {item.severity for item in violations} >= {"CRITICAL", "MAJOR"}


def test_score_floors_at_zero() -> None:
    _, score, _ = engine.evaluate(
        ExtractedLabelData(
            mrp=None,
            net_quantity=None,
            manufacturer_details=None,
            date_of_packing=None,
            country_of_origin=None,
            consumer_care=None,
        )
    )
    assert score == 0
