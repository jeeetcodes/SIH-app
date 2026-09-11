from app.schemas.scan import ExtractedLabelData
from app.services.rules_engine import RulesEngine

engine = RulesEngine()


def _fields(**overrides) -> ExtractedLabelData:
    base = dict(
        product_name="Acme Namkeen",
        product_category="General Grocery",
        mrp="Rs. 150.00 incl. of all taxes",
        net_quantity="500 g",
        manufacturer_details="Acme Foods Pvt Ltd, Plot 12, MIDC, Pune, Maharashtra 411019, India",
        date_of_packing="08/2026",
        expiry_date="Best before 12 months",
        country_of_origin="India",
        consumer_care="care@acmefoods.example | 9876543210",
        unit_sale_price="Rs. 0.30/g",
        ingredients="Gram flour, edible oil, salt",
        formatting_assessment="Clear print",
    )
    base.update(overrides)
    return ExtractedLabelData(**base)


def test_compliant_label_scores_100() -> None:
    status, score, violations = engine.evaluate(_fields())
    assert status == "COMPLIANT"
    assert score == 100
    assert violations == []


def test_missing_mrp_is_critical() -> None:
    status, score, violations = engine.evaluate(_fields(mrp=None))
    assert status == "NON_COMPLIANT"
    assert score == 75
    assert any(item.rule_id == "LM-PCR-6-1-e" and item.severity == "CRITICAL" for item in violations)


def test_mrp_without_inclusive_taxes_is_critical() -> None:
    status, score, violations = engine.evaluate(_fields(mrp="Rs. 99.00"))
    assert status == "NON_COMPLIANT"
    assert any("incl" in item.message.lower() for item in violations)


def test_missing_consumer_care_is_critical() -> None:
    status, score, violations = engine.evaluate(_fields(consumer_care=None))
    assert status == "NON_COMPLIANT"
    assert score == 75
    assert any(item.rule_id == "LM-PCR-6-1-h" and item.severity == "CRITICAL" for item in violations)


def test_missing_fssai_for_food_is_critical() -> None:
    status, score, violations = engine.evaluate(
        _fields(product_category="Food & Beverage", fssai_license=None)
    )
    assert status == "NON_COMPLIANT"
    assert any(item.rule_id == "FSSAI-SEC-31" and item.severity == "CRITICAL" for item in violations)


def test_invalid_net_quantity_unit_gms() -> None:
    _, score, violations = engine.evaluate(_fields(net_quantity="500 gms"))
    assert any(item.field_name == "net_quantity" and item.severity == "MAJOR" for item in violations)
    assert score == 85


def test_lbs_unit_is_rejected() -> None:
    _, _, violations = engine.evaluate(_fields(net_quantity="1 lbs"))
    assert any(item.field_name == "net_quantity" for item in violations)


def test_consumer_care_requires_phone_or_email() -> None:
    _, _, violations = engine.evaluate(_fields(consumer_care="customer desk"))
    assert any(item.rule_id == "LM-PCR-6-1-h" and item.severity == "CRITICAL" for item in violations)


def test_missing_consumer_care_email_is_major() -> None:
    status, score, violations = engine.evaluate(_fields(consumer_care="9876543210"))
    assert score == 90
    assert any("email" in item.message.lower() for item in violations)


def test_missing_packing_date_is_major() -> None:
    _, score, violations = engine.evaluate(_fields(date_of_packing=None))
    assert score == 90
    assert any(item.rule_id == "LM-PCR-6-1-d" and item.severity == "MAJOR" for item in violations)


def test_incomplete_manufacturer_address_is_major() -> None:
    _, score, violations = engine.evaluate(_fields(manufacturer_details="BrandX"))
    assert score == 85
    assert any(item.rule_id == "LM-PCR-6-1-a" and item.severity == "MAJOR" for item in violations)


def test_formatting_issue_is_minor() -> None:
    status, score, violations = engine.evaluate(
        _fields(formatting_assessment="Font size too small on ingredients panel")
    )
    assert status == "COMPLIANT"
    assert score == 95
    assert any(item.severity == "MINOR" and item.penalty == 5 for item in violations)


def test_missing_ingredients_for_food_is_minor() -> None:
    status, score, violations = engine.evaluate(
        _fields(product_category="Food & Beverage", fssai_license="10012011000123", ingredients=None)
    )
    assert status == "COMPLIANT"
    assert score == 95
    assert any(item.rule_id == "LM-PCR-INGREDIENTS" and item.severity == "MINOR" for item in violations)


def test_imported_missing_origin_is_minor() -> None:
    status, score, violations = engine.evaluate(
        _fields(
            country_of_origin=None,
            manufacturer_details="Imported by Acme Traders, Plot 9, Andheri, Mumbai 400053",
        )
    )
    assert status == "COMPLIANT"
    assert score == 95
    assert any(item.rule_id == "LM-PCR-6-1-aa" and item.severity == "MINOR" for item in violations)


def test_score_floors_at_zero() -> None:
    _, score, _ = engine.evaluate(
        ExtractedLabelData(
            product_category="Food & Beverage",
            mrp=None,
            net_quantity=None,
            manufacturer_details=None,
            date_of_packing=None,
            country_of_origin=None,
            consumer_care=None,
            fssai_license=None,
        )
    )
    assert score == 0
