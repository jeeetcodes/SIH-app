from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ScanRecord(Base):
    """Compact, query-friendly history entry for a completed label scan."""

    __tablename__ = "scan_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    product_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    is_compliant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    violations_json: Mapped[str] = mapped_column(Text, nullable=False)
    raw_extracted_data: Mapped[str] = mapped_column(Text, nullable=False)
