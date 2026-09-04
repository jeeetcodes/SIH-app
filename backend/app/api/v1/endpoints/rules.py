from fastapi import APIRouter

from app.core.constants import LEGAL_METROLOGY_GUIDELINES, VALID_SI_UNITS

router = APIRouter()


@router.get("")
def list_guidelines() -> dict:
    return {
        "valid_si_units": sorted(VALID_SI_UNITS),
        "guidelines": LEGAL_METROLOGY_GUIDELINES,
    }
