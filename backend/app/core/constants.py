"""Indian Legal Metrology (Packaged Commodities) Rule 6 defaults."""

VALID_WEIGHT_UNITS = frozenset({"g", "kg"})
VALID_VOLUME_UNITS = frozenset({"ml", "l", "L"})
VALID_LENGTH_AREA_UNITS = frozenset({"cm", "m", "sq cm", "sq m"})
VALID_COUNT_UNITS = frozenset({"n", "u", "units", "pcs"})

# Canonical SI / permitted metric units for net quantity declarations.
VALID_SI_UNITS = (
    VALID_WEIGHT_UNITS
    | VALID_VOLUME_UNITS
    | VALID_LENGTH_AREA_UNITS
    | VALID_COUNT_UNITS
)

# Common non-standard labels that must not be treated as valid SI units.
INVALID_QUANTITY_UNITS = frozenset(
    {
        "gm",
        "gms",
        "grms",
        "grams",
        "kilo",
        "kilos",
        "kgs",
        "lb",
        "lbs",
        "oz",
        "ounce",
        "ounces",
        "pound",
        "pounds",
    }
)

MANDATORY_LABEL_FIELDS = (
    "mrp",
    "net_quantity",
    "manufacturer_details",
    "date_of_packing",
    "consumer_care",
)

RULE_CITATIONS = {
    "mrp": "Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(e)",
    "net_quantity": "Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(c)",
    "consumer_care": "Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(h)",
    "date_of_packing": "Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(d)",
    "manufacturer_details": "Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(a)",
    "country_of_origin": "Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(aa)",
    "fssai_license": "FSS (Packaging and Labelling) Regulations, 2011 & Legal Metrology Act, 2009",
    "expiry_date": "Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(d) & FSSR 2011",
    "ingredients": "Legal Metrology (Packaged Commodities) Rules, 2011 & Product Composition Norms",
    "formatting": "Legal Metrology (Packaged Commodities) Rules, 2011, Rule 7 & Rule 9",
}

LEGAL_METROLOGY_GUIDELINES = [
    {
        "rule_id": "LM-PCR-6-1-a",
        "field_name": "manufacturer_details",
        "citation": RULE_CITATIONS["manufacturer_details"],
        "summary": "Name and complete address of the manufacturer, packer, or importer must be declared.",
    },
    {
        "rule_id": "LM-PCR-6-1-aa",
        "field_name": "country_of_origin",
        "citation": RULE_CITATIONS["country_of_origin"],
        "summary": "Country of origin must be declared on imported packaged commodities.",
    },
    {
        "rule_id": "LM-PCR-6-1-c",
        "field_name": "net_quantity",
        "citation": RULE_CITATIONS["net_quantity"],
        "summary": "Net quantity must be declared in standard SI metric units (g, kg, ml, l, etc.).",
    },
    {
        "rule_id": "LM-PCR-6-1-d",
        "field_name": "date_of_packing",
        "citation": RULE_CITATIONS["date_of_packing"],
        "summary": "Month and year of manufacture, packing, or import must be declared.",
    },
    {
        "rule_id": "LM-PCR-6-1-e",
        "field_name": "mrp",
        "citation": RULE_CITATIONS["mrp"],
        "summary": "Maximum retail price must be declared inclusive of all taxes.",
    },
    {
        "rule_id": "LM-PCR-6-1-h",
        "field_name": "consumer_care",
        "citation": RULE_CITATIONS["consumer_care"],
        "summary": "Consumer care telephone number, email, or both must be declared.",
    },
]
