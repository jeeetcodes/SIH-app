from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ExtractedLabelData(BaseModel):
    """Mandatory Legal Metrology declarations extracted from a packaging image."""

    model_config = ConfigDict(extra="ignore")

    product_name: Optional[str] = Field(
        default=None,
        description="Product or brand name shown on the package label.",
    )
    product_category: Optional[str] = Field(
        default=None,
        description="Classified category: Food & Beverage, Cosmetics, Electronics, General Grocery, Medical/FMCG, or Other.",
    )
    mrp: Optional[str] = Field(
        default=None,
        description='Retail price declaration, e.g. "Rs. 150.00 incl. of all taxes".',
    )
    net_quantity: Optional[str] = Field(
        default=None,
        description='Net content declaration, e.g. "500 g".',
    )
    manufacturer_details: Optional[str] = Field(
        default=None,
        description="Name and complete address of manufacturer, packer, or importer.",
    )
    date_of_packing: Optional[str] = Field(
        default=None,
        description='Month and year of manufacture/packing, e.g. "08/2026".',
    )
    expiry_date: Optional[str] = Field(
        default=None,
        description='Expiry date or best before date where declared, e.g. "Best before 12 months from mfg".',
    )
    country_of_origin: Optional[str] = Field(
        default=None,
        description="Country of origin for imported commodities.",
    )
    consumer_care: Optional[str] = Field(
        default=None,
        description="Consumer care telephone number and/or email address and postal address.",
    )
    unit_sale_price: Optional[str] = Field(
        default=None,
        description='Unit sale price where declared, e.g. "Rs. 0.30/g".',
    )
    fssai_license: Optional[str] = Field(
        default=None,
        description="14-digit FSSAI License number if food or beverage product.",
    )
    ingredients: Optional[str] = Field(
        default=None,
        description="Generic ingredients or composition list where declared.",
    )
    formatting_assessment: Optional[str] = Field(
        default=None,
        description="Assessment of font height, contrast, or readability issues.",
    )
    is_packaging_label: Optional[bool] = Field(
        default=None,
        description="Whether the image clearly contains a consumer-package label.",
    )
    image_assessment: Optional[str] = Field(
        default=None,
        description="Brief reason when the image is not a readable package label.",
    )


class Violation(BaseModel):
    rule_id: str
    rule_name: Optional[str] = None
    field_name: str
    severity: Literal["CRITICAL", "MAJOR", "MINOR", "WARNING", "critical", "major", "minor"]
    penalty: int = 0
    message: str
    explanation: Optional[str] = None
    citation: str

    def model_post_init(self, __context) -> None:
        if not self.explanation:
            self.explanation = self.message
        if not self.rule_name:
            self.rule_name = self.rule_id


class ScanResponse(BaseModel):
    scan_id: str
    status: Literal["COMPLIANT", "NON_COMPLIANT"]
    final_score: int = Field(ge=0, le=100)
    overall_score: int = Field(ge=0, le=100)
    product_category: Optional[str] = None
    extracted_data: ExtractedLabelData
    violations: List[Violation]
    used_mock_vision: bool = False
    is_packaging_label: Optional[bool] = None
    image_assessment: Optional[str] = None


class ScanHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    product_name: Optional[str]
    score: int = Field(ge=0, le=100)
    is_compliant: bool
