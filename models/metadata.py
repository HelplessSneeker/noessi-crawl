"""Lightweight metadata for apartment tracking and summary generation."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ApartmentMetadata:
    """
    Lightweight metadata for summary generation and top-N tracking.

    Contains only essential fields needed for summary tables and ranking,
    providing ~77% memory reduction compared to full ApartmentListing objects.
    """

    # Identity
    listing_id: str
    filename: str  # Relative path: apartments/2025-12-06_8.5_Wien_250000.md

    # Scoring & recommendation
    investment_score: Optional[float]
    recommendation: Optional[str]

    # Financial metrics (for summary table)
    price: Optional[float]
    size_sqm: Optional[float]
    price_per_sqm: Optional[float]
    gross_yield: Optional[float]
    net_yield: Optional[float]
    monthly_cash_flow: Optional[float]

    # Location (for display)
    city: Optional[str]
    postal_code: Optional[str]
    district: Optional[str]

    # Title for reference
    title: Optional[str]

    # Source URL
    source_url: str

    # Validation status
    validation_failed: bool = False
    validation_reason: Optional[str] = None

    # Timestamp
    scraped_at: datetime = field(default_factory=datetime.now)
