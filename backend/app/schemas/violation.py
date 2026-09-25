from typing import List, Literal

from pydantic import BaseModel

from app.schemas.scan import Violation


class ComplianceReport(BaseModel):
    status: Literal["COMPLIANT", "NON_COMPLIANT"]
    overall_score: int
    violations: List[Violation]
