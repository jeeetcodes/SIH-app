from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

from app.core.constants import (
    INVALID_QUANTITY_UNITS,
    RULE_CITATIONS,
    VALID_COUNT_UNITS,
    VALID_LENGTH_AREA_UNITS,
    VALID_VOLUME_UNITS,
    VALID_WEIGHT_UNITS,
)
from app.schemas.scan import ExtractedLabelData, Violation

logger = logging.getLogger(__name__)

MRP_INCLUSIVE_PATTERN = re.compile(
    r"(incl\.?\s*of\s*all\s*taxes|inclusive\s+of\s+all\s+taxes)",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.IGNORECASE)
PHONE_PATTERN = re.compile(
    r"(?:\+?91[\s\-]?)?[6-9]\d{9}|\b\d{5}[\s\-]\d{5}\b|\b\d{10,12}\b"
)
DATE_PATTERN = re.compile(
    r"""
    \b(?:0?[1-9]|1[0-2])[/\-](?:\d{2}|\d{4})\b
    |
    \b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|
       jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|
       nov(?:ember)?|dec(?:ember)?)
       [.\s\-/]+\d{2,4}\b
    """,
    re.IGNORECASE | re.VERBOSE,
)
ADDRESS_HINT_PATTERN = re.compile(
    r"\b(road|rd|street|st|marg|nagar|plot|sector|phase|village|dist|"
    r"district|taluk|tehsil|pincode|pin|india|state|ltd|pvt|limited|"
    r"industrial|area|block|floor|building|estate|midc)\b",
    re.IGNORECASE,
)
PINCODE_PATTERN = re.compile(r"\b\d{6}\b")
IMPORTED_HINT_PATTERN = re.compile(
    r"\b(imported|import(?:ed)?\s+by|made\s+in\s+(?!india\b)[a-z]+)\b",
    re.IGNORECASE,
)
INDIA_ORIGIN_PATTERN = re.compile(r"\b(india|bharat|hindustan)\b", re.IGNORECASE)

MULTI_WORD_UNITS = ("sq cm", "sq m")

# Legal Metrology (Packaged Commodities) Rules, 2011 Severity Weights
PENALTY_CRITICAL = 25
PENALTY_MAJOR_NET_QTY = 15
PENALTY_MAJOR_MFG = 15
PENALTY_MAJOR_DATE = 10
PENALTY_MINOR = 5


class RulesEngine:
    """Deterministic Legal Metrology (Packaged Commodities) Rules, 2011 compliance auditor."""

    def evaluate(self, extracted: ExtractedLabelData) -> Tuple[str, int, List[Violation]]:
        violations: List[Violation] = []
        try:
            # 1. CRITICAL RULES (-20 to -30 points each)
            violations.extend(self._check_mrp(extracted.mrp))
            violations.extend(self._check_consumer_care(extracted.consumer_care))
            violations.extend(self._check_fssai(extracted))

            # 2. MAJOR RULES (-10 to -15 points each)
            violations.extend(self._check_net_quantity(extracted.net_quantity))
            violations.extend(self._check_dates(extracted))
            violations.extend(self._check_manufacturer(extracted.manufacturer_details))

            # 3. MINOR RULES (-5 points each)
            violations.extend(self._check_formatting(extracted.formatting_assessment))
            violations.extend(self._check_ingredients(extracted))
            violations.extend(self._check_country_of_origin(extracted))

        except Exception:
            logger.exception("Rules engine failed unexpectedly; returning safe fallback")
            violations.append(
                Violation(
                    rule_id="LM-ENGINE-ERROR",
                    rule_name="Internal Audit Engine Safeguard",
                    field_name="extracted_data",
                    severity="WARNING",
                    penalty=5,
                    message="Compliance evaluation encountered an internal error. Treat this result as incomplete.",
                    explanation="Compliance evaluation encountered an internal error. Treat this result as incomplete.",
                    citation="Internal rules engine safeguard",
                )
            )

        overall_score = self._score(violations)
        blocking = any(item.severity.upper() == "CRITICAL" for item in violations) or overall_score < 75
        status = "NON_COMPLIANT" if blocking else "COMPLIANT"
        return status, overall_score, violations

    def _score(self, violations: List[Violation]) -> int:
        deductions = sum(v.penalty for v in violations)
        return max(0, min(100, 100 - deductions))

    def _blank(self, value: Optional[str]) -> bool:
        return value is None or not str(value).strip() or str(value).strip().lower() in {
            "null",
            "n/a",
            "na",
            "none",
            "unknown",
            "not visible",
            "unreadable",
            "not detected",
        }

    # -------------------------------------------------------------------------
    # CRITICAL CHECKS
    # -------------------------------------------------------------------------

    def _check_mrp(self, mrp: Optional[str]) -> List[Violation]:
        """Rule 6(1)(e): Maximum Retail Price with inclusive taxes."""
        if self._blank(mrp):
            return [
                self._violation(
                    rule_id="LM-PCR-6-1-e",
                    rule_name="Maximum Retail Price (MRP)",
                    field_name="mrp",
                    severity="CRITICAL",
                    penalty=PENALTY_CRITICAL,
                    message="MRP is missing from the label.",
                    citation=RULE_CITATIONS["mrp"],
                )
            ]
        if not MRP_INCLUSIVE_PATTERN.search(mrp or ""):
            return [
                self._violation(
                    rule_id="LM-PCR-6-1-e",
                    rule_name="Maximum Retail Price (MRP)",
                    field_name="mrp",
                    severity="CRITICAL",
                    penalty=PENALTY_CRITICAL,
                    message='MRP must include the phrase "incl. of all taxes" or "inclusive of all taxes".',
                    citation=RULE_CITATIONS["mrp"],
                )
            ]
        return []

    def _check_consumer_care(self, consumer_care: Optional[str]) -> List[Violation]:
        """Rule 6(1)(h): Consumer Care Details (phone, email, and address)."""
        if self._blank(consumer_care):
            return [
                self._violation(
                    rule_id="LM-PCR-6-1-h",
                    rule_name="Consumer Care Details",
                    field_name="consumer_care",
                    severity="CRITICAL",
                    penalty=PENALTY_CRITICAL,
                    message="Consumer care details (phone number, email, and address) are missing.",
                    citation=RULE_CITATIONS["consumer_care"],
                )
            ]
        text = consumer_care or ""
        has_email = bool(EMAIL_PATTERN.search(text))
        has_phone = bool(PHONE_PATTERN.search(text))
        if not has_email and not has_phone:
            return [
                self._violation(
                    rule_id="LM-PCR-6-1-h",
                    rule_name="Consumer Care Details",
                    field_name="consumer_care",
                    severity="CRITICAL",
                    penalty=PENALTY_CRITICAL,
                    message="Consumer care declaration does not contain a telephone number or email address.",
                    citation=RULE_CITATIONS["consumer_care"],
                )
            ]
        if has_phone and not has_email:
            return [
                self._violation(
                    rule_id="LM-PCR-6-1-h",
                    rule_name="Consumer Care Email",
                    field_name="consumer_care",
                    severity="MAJOR",
                    penalty=PENALTY_MAJOR_DATE,
                    message="Consumer care email address is missing from the label.",
                    citation=RULE_CITATIONS["consumer_care"],
                )
            ]
        return []

    def _check_fssai(self, extracted: ExtractedLabelData) -> List[Violation]:
        """FSSAI License Number required for Food & Beverage products."""
        category = (extracted.product_category or "").strip().lower()
        is_food = "food" in category or "beverage" in category or "snack" in category or "drink" in category
        if not is_food:
            return []

        if self._blank(extracted.fssai_license):
            return [
                self._violation(
                    rule_id="FSSAI-SEC-31",
                    rule_name="FSSAI License Number",
                    field_name="fssai_license",
                    severity="CRITICAL",
                    penalty=PENALTY_CRITICAL,
                    message="Missing FSSAI License Number (mandatory for Food & Beverage products in India).",
                    citation=RULE_CITATIONS["fssai_license"],
                )
            ]
        return []

    # -------------------------------------------------------------------------
    # MAJOR CHECKS
    # -------------------------------------------------------------------------

    def _check_net_quantity(self, net_quantity: Optional[str]) -> List[Violation]:
        """Rule 6(1)(c): Net quantity declared in standard SI metric units."""
        if self._blank(net_quantity):
            return [
                self._violation(
                    rule_id="LM-PCR-6-1-c",
                    rule_name="Net Quantity Declaration",
                    field_name="net_quantity",
                    severity="MAJOR",
                    penalty=PENALTY_MAJOR_NET_QTY,
                    message="Net quantity is missing from the label.",
                    citation=RULE_CITATIONS["net_quantity"],
                )
            ]
        unit = self._extract_unit(net_quantity or "")
        if unit is None:
            return [
                self._violation(
                    rule_id="LM-PCR-6-1-c",
                    rule_name="Net Quantity Unit",
                    field_name="net_quantity",
                    severity="MAJOR",
                    penalty=PENALTY_MAJOR_NET_QTY,
                    message=f'Net quantity "{net_quantity}" does not declare a recognized SI metric unit.',
                    citation=RULE_CITATIONS["net_quantity"],
                )
            ]
        if unit in INVALID_QUANTITY_UNITS:
            return [
                self._violation(
                    rule_id="LM-PCR-6-1-c",
                    rule_name="Net Quantity Non-Standard Unit",
                    field_name="net_quantity",
                    severity="MAJOR",
                    penalty=PENALTY_MAJOR_NET_QTY,
                    message=f'Net quantity uses a non-standard unit "{unit}". Use SI metric units such as g, kg, ml, or l.',
                    citation=RULE_CITATIONS["net_quantity"],
                )
            ]
        if not self._is_valid_si_unit(unit):
            return [
                self._violation(
                    rule_id="LM-PCR-6-1-c",
                    rule_name="Net Quantity Metric Unit",
                    field_name="net_quantity",
                    severity="MAJOR",
                    penalty=PENALTY_MAJOR_NET_QTY,
                    message=f'Net quantity unit "{unit}" is not a permitted SI metric unit under Legal Metrology.',
                    citation=RULE_CITATIONS["net_quantity"],
                )
            ]
        return []

    def _check_dates(self, extracted: ExtractedLabelData) -> List[Violation]:
        """Rule 6(1)(d): Month & Year of Mfg/Packing and Expiry/Best Before date."""
        violations: List[Violation] = []
        dop = extracted.date_of_packing
        if self._blank(dop):
            violations.append(
                self._violation(
                    rule_id="LM-PCR-6-1-d",
                    rule_name="Date of Manufacture / Packing",
                    field_name="date_of_packing",
                    severity="MAJOR",
                    penalty=PENALTY_MAJOR_DATE,
                    message="Date of manufacture/packing (month and year) is missing.",
                    citation=RULE_CITATIONS["date_of_packing"],
                )
            )
        elif not DATE_PATTERN.search(dop or ""):
            violations.append(
                self._violation(
                    rule_id="LM-PCR-6-1-d",
                    rule_name="Date of Manufacture Format",
                    field_name="date_of_packing",
                    severity="MAJOR",
                    penalty=PENALTY_MAJOR_DATE,
                    message=f'Date of packing "{dop}" does not include a recognizable month and year.',
                    citation=RULE_CITATIONS["date_of_packing"],
                )
            )

        # Expiry / Best Before check for perishable/consumable products
        category = (extracted.product_category or "").strip().lower()
        needs_expiry = any(c in category for c in ("food", "beverage", "cosmetic", "medical", "fmcg"))
        if needs_expiry and self._blank(extracted.expiry_date):
            violations.append(
                self._violation(
                    rule_id="LM-PCR-6-1-d-exp",
                    rule_name="Expiry / Best Before Date",
                    field_name="expiry_date",
                    severity="MAJOR",
                    penalty=PENALTY_MAJOR_DATE,
                    message="Expiry date or Best Before declaration is missing for consumable product.",
                    citation=RULE_CITATIONS["expiry_date"],
                )
            )

        return violations

    def _check_manufacturer(self, manufacturer_details: Optional[str]) -> List[Violation]:
        """Rule 6(1)(a): Complete name and address of manufacturer, packer, or importer."""
        if self._blank(manufacturer_details):
            return [
                self._violation(
                    rule_id="LM-PCR-6-1-a",
                    rule_name="Manufacturer / Packer Details",
                    field_name="manufacturer_details",
                    severity="MAJOR",
                    penalty=PENALTY_MAJOR_MFG,
                    message="Manufacturer, packer, or importer name and address are missing.",
                    citation=RULE_CITATIONS["manufacturer_details"],
                )
            ]
        text = (manufacturer_details or "").strip()
        has_complete_address = (
            len(text) >= 20
            and (bool(PINCODE_PATTERN.search(text)) or bool(ADDRESS_HINT_PATTERN.search(text)))
            and any(ch.isdigit() for ch in text)
        )
        if not has_complete_address:
            return [
                self._violation(
                    rule_id="LM-PCR-6-1-a",
                    rule_name="Manufacturer Physical Address",
                    field_name="manufacturer_details",
                    severity="MAJOR",
                    penalty=PENALTY_MAJOR_MFG,
                    message="Manufacturer/packer declaration does not include a complete address.",
                    citation=RULE_CITATIONS["manufacturer_details"],
                )
            ]
        return []

    # -------------------------------------------------------------------------
    # MINOR CHECKS
    # -------------------------------------------------------------------------

    def _check_formatting(self, formatting_assessment: Optional[str]) -> List[Violation]:
        """Rule 7 & 9: Font height, contrast, and visual legibility."""
        if self._blank(formatting_assessment):
            return []
        assessment = formatting_assessment.strip().lower()
        negative_keywords = ("too small", "poor contrast", "illegible", "obscured", "blurry", "faded", "unreadable", "hard to read")
        if any(kw in assessment for kw in negative_keywords):
            return [
                self._violation(
                    rule_id="LM-PCR-RULE-7",
                    rule_name="Label Formatting & Legibility",
                    field_name="formatting_assessment",
                    severity="MINOR",
                    penalty=PENALTY_MINOR,
                    message=f"Formatting issue detected: {formatting_assessment.strip()}",
                    citation=RULE_CITATIONS["formatting"],
                )
            ]
        return []

    def _check_ingredients(self, extracted: ExtractedLabelData) -> List[Violation]:
        """Generic ingredients list for food, cosmetics, and FMCG."""
        category = (extracted.product_category or "").strip().lower()
        needs_ingredients = any(c in category for c in ("food", "beverage", "cosmetic", "fmcg"))
        if needs_ingredients and self._blank(extracted.ingredients):
            return [
                self._violation(
                    rule_id="LM-PCR-INGREDIENTS",
                    rule_name="Ingredients Declaration",
                    field_name="ingredients",
                    severity="MINOR",
                    penalty=PENALTY_MINOR,
                    message="Ingredients or composition list is missing from the package label.",
                    citation=RULE_CITATIONS["ingredients"],
                )
            ]
        return []

    def _check_country_of_origin(self, extracted: ExtractedLabelData) -> List[Violation]:
        """Rule 6(1)(aa): Country of origin on imported packages."""
        if not self._is_likely_imported(extracted):
            return []
        if not self._blank(extracted.country_of_origin):
            return []
        return [
            self._violation(
                rule_id="LM-PCR-6-1-aa",
                rule_name="Country of Origin",
                field_name="country_of_origin",
                severity="MINOR",
                penalty=PENALTY_MINOR,
                message="Package appears imported but country of origin is not declared.",
                citation=RULE_CITATIONS["country_of_origin"],
            )
        ]

    def _is_likely_imported(self, extracted: ExtractedLabelData) -> bool:
        origin = extracted.country_of_origin
        if origin and not self._blank(origin) and not INDIA_ORIGIN_PATTERN.search(origin):
            return True
        blob = " ".join(
            part
            for part in (
                extracted.manufacturer_details,
                extracted.country_of_origin,
                extracted.mrp,
                extracted.consumer_care,
            )
            if part
        )
        return bool(IMPORTED_HINT_PATTERN.search(blob))

    def _extract_unit(self, net_quantity: str) -> Optional[str]:
        normalized = re.sub(r"\s+", " ", net_quantity.strip().lower())
        for multi in MULTI_WORD_UNITS:
            if re.search(rf"\b{re.escape(multi)}\b", normalized):
                return multi
        match = re.search(r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)", net_quantity)
        if match:
            return match.group(2).strip().lower()
        tokens = re.findall(r"[a-zA-Z]+", normalized)
        return tokens[-1] if tokens else None

    def _is_valid_si_unit(self, unit: str) -> bool:
        lowered = unit.lower()
        if lowered in VALID_WEIGHT_UNITS:
            return True
        if lowered in VALID_VOLUME_UNITS:
            return True
        if lowered in VALID_LENGTH_AREA_UNITS:
            return True
        if lowered in VALID_COUNT_UNITS:
            return True
        return False

    def _violation(
        self,
        rule_id: str,
        rule_name: str,
        field_name: str,
        severity: str,
        penalty: int,
        message: str,
        citation: str,
    ) -> Violation:
        return Violation(
            rule_id=rule_id,
            rule_name=rule_name,
            field_name=field_name,
            severity=severity,  # type: ignore[arg-type]
            penalty=penalty,
            message=message,
            explanation=message,
            citation=citation,
        )
