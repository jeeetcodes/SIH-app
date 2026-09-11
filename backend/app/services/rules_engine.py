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

CRITICAL_PENALTY = 25
MAJOR_PENALTY = 10
WARNING_PENALTY = 5


class RulesEngine:
    """Deterministic Legal Metrology (Packaged Commodities) Rule 6 checker."""

    def evaluate(self, extracted: ExtractedLabelData) -> Tuple[str, int, List[Violation]]:
        violations: List[Violation] = []
        try:
            violations.extend(self._check_mrp(extracted.mrp))
            violations.extend(self._check_net_quantity(extracted.net_quantity))
            violations.extend(self._check_consumer_care(extracted.consumer_care))
            violations.extend(self._check_date_of_packing(extracted.date_of_packing))
            violations.extend(self._check_manufacturer(extracted.manufacturer_details))
            violations.extend(self._check_country_of_origin(extracted))
        except Exception:
            logger.exception("Rules engine failed unexpectedly; returning safe fallback")
            violations.append(
                Violation(
                    rule_id="LM-ENGINE-ERROR",
                    field_name="extracted_data",
                    severity="WARNING",
                    message="Compliance evaluation encountered an internal error. Treat this result as incomplete.",
                    citation="Internal rules engine safeguard",
                )
            )

        overall_score = self._score(violations)
        blocking = any(item.severity in {"CRITICAL", "MAJOR"} for item in violations)
        status = "NON_COMPLIANT" if blocking else "COMPLIANT"
        return status, overall_score, violations

    def _score(self, violations: List[Violation]) -> int:
        score = 100
        for item in violations:
            if item.severity == "CRITICAL":
                score -= CRITICAL_PENALTY
            elif item.severity == "MAJOR":
                score -= MAJOR_PENALTY
            else:
                score -= WARNING_PENALTY
        return max(0, min(100, score))

    def _blank(self, value: Optional[str]) -> bool:
        return value is None or not str(value).strip() or str(value).strip().lower() in {
            "null",
            "n/a",
            "na",
            "none",
            "unknown",
            "not visible",
            "unreadable",
        }

    def _check_mrp(self, mrp: Optional[str]) -> List[Violation]:
        if self._blank(mrp):
            return [
                self._violation(
                    "LM-PCR-6-1-e",
                    "mrp",
                    "CRITICAL",
                    "MRP is missing from the label.",
                    RULE_CITATIONS["mrp"],
                )
            ]
        if not MRP_INCLUSIVE_PATTERN.search(mrp or ""):
            return [
                self._violation(
                    "LM-PCR-6-1-e",
                    "mrp",
                    "CRITICAL",
                    'MRP must include the phrase "incl. of all taxes" or "inclusive of all taxes".',
                    RULE_CITATIONS["mrp"],
                )
            ]
        return []

    def _check_net_quantity(self, net_quantity: Optional[str]) -> List[Violation]:
        if self._blank(net_quantity):
            return [
                self._violation(
                    "LM-PCR-6-1-c",
                    "net_quantity",
                    "CRITICAL",
                    "Net quantity is missing from the label.",
                    RULE_CITATIONS["net_quantity"],
                )
            ]
        unit = self._extract_unit(net_quantity or "")
        if unit is None:
            return [
                self._violation(
                    "LM-PCR-6-1-c",
                    "net_quantity",
                    "CRITICAL",
                    f'Net quantity "{net_quantity}" does not declare a recognized SI metric unit.',
                    RULE_CITATIONS["net_quantity"],
                )
            ]
        if unit in INVALID_QUANTITY_UNITS:
            return [
                self._violation(
                    "LM-PCR-6-1-c",
                    "net_quantity",
                    "CRITICAL",
                    f'Net quantity uses a non-standard unit "{unit}". Use SI metric units such as g, kg, ml, or l.',
                    RULE_CITATIONS["net_quantity"],
                )
            ]
        if not self._is_valid_si_unit(unit):
            return [
                self._violation(
                    "LM-PCR-6-1-c",
                    "net_quantity",
                    "CRITICAL",
                    f'Net quantity unit "{unit}" is not a permitted SI metric unit under Legal Metrology.',
                    RULE_CITATIONS["net_quantity"],
                )
            ]
        return []

    def _check_consumer_care(self, consumer_care: Optional[str]) -> List[Violation]:
        if self._blank(consumer_care):
            return [
                self._violation(
                    "LM-PCR-6-1-h",
                    "consumer_care",
                    "MAJOR",
                    "Consumer care details are missing. A telephone number or email address is required.",
                    RULE_CITATIONS["consumer_care"],
                )
            ]
        text = consumer_care or ""
        has_email = bool(EMAIL_PATTERN.search(text))
        has_phone = bool(PHONE_PATTERN.search(text))
        if not has_email and not has_phone:
            return [
                self._violation(
                    "LM-PCR-6-1-h",
                    "consumer_care",
                    "MAJOR",
                    "Consumer care declaration does not contain a telephone number or email address.",
                    RULE_CITATIONS["consumer_care"],
                )
            ]
        if has_phone and not has_email:
            return [
                self._violation(
                    "LM-PCR-6-1-h",
                    "consumer_care",
                    "MAJOR",
                    "Consumer care email is missing from the label.",
                    RULE_CITATIONS["consumer_care"],
                )
            ]
        return []

    def _check_date_of_packing(self, date_of_packing: Optional[str]) -> List[Violation]:
        if self._blank(date_of_packing):
            return [
                self._violation(
                    "LM-PCR-6-1-d",
                    "date_of_packing",
                    "CRITICAL",
                    "Date of manufacture/packing (month and year) is missing.",
                    RULE_CITATIONS["date_of_packing"],
                )
            ]
        if not DATE_PATTERN.search(date_of_packing or ""):
            return [
                self._violation(
                    "LM-PCR-6-1-d",
                    "date_of_packing",
                    "CRITICAL",
                    f'Date of packing "{date_of_packing}" does not include a recognizable month and year.',
                    RULE_CITATIONS["date_of_packing"],
                )
            ]
        return []

    def _check_manufacturer(self, manufacturer_details: Optional[str]) -> List[Violation]:
        if self._blank(manufacturer_details):
            return [
                self._violation(
                    "LM-PCR-6-1-a",
                    "manufacturer_details",
                    "CRITICAL",
                    "Manufacturer, packer, or importer name and address are missing.",
                    RULE_CITATIONS["manufacturer_details"],
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
                    "LM-PCR-6-1-a",
                    "manufacturer_details",
                    "CRITICAL",
                    "Manufacturer/packer declaration does not include a complete address.",
                    RULE_CITATIONS["manufacturer_details"],
                )
            ]
        return []

    def _check_country_of_origin(self, extracted: ExtractedLabelData) -> List[Violation]:
        if not self._is_likely_imported(extracted):
            return []
        if not self._blank(extracted.country_of_origin):
            return []
        return [
            self._violation(
                "LM-PCR-6-1-aa",
                "country_of_origin",
                "WARNING",
                "Package appears imported but country of origin is not declared.",
                RULE_CITATIONS["country_of_origin"],
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
        field_name: str,
        severity: str,
        message: str,
        citation: str,
    ) -> Violation:
        return Violation(
            rule_id=rule_id,
            field_name=field_name,
            severity=severity,  # type: ignore[arg-type]
            message=message,
            citation=citation,
        )
