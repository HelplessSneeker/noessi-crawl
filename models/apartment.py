"""Apartment listing data model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .constants import RENT_PER_SQM_DEFAULTS, TRANSACTION_COSTS, VIENNA_DISTRICTS


@dataclass
class ApartmentListing:
    """Comprehensive data model for Austrian apartment listings."""

    # Core identifiers
    listing_id: str
    source_url: str
    source_portal: str = "willhaben"
    scraped_at: datetime = field(default_factory=datetime.now)

    # Address information
    street: Optional[str] = None
    house_number: Optional[str] = None
    door_number: Optional[str] = None
    district: Optional[str] = None
    district_number: Optional[int] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    full_address: Optional[str] = None

    # Financial information
    price: Optional[float] = None
    price_per_sqm: Optional[float] = None
    betriebskosten_monthly: Optional[float] = None
    betriebskosten_per_sqm: Optional[float] = None
    reparaturrucklage: Optional[float] = None
    heating_cost_monthly: Optional[float] = None
    total_monthly_cost: Optional[float] = None

    # Property specifications
    title: Optional[str] = None
    size_sqm: Optional[float] = None
    rooms: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    floor: Optional[int] = None
    floor_text: Optional[str] = None
    total_floors: Optional[int] = None
    year_built: Optional[int] = None
    year_renovated: Optional[int] = None
    condition: Optional[str] = None
    building_type: Optional[str] = None

    # Features
    elevator: Optional[bool] = None
    balcony: Optional[bool] = None
    terrace: Optional[bool] = None
    loggia: Optional[bool] = None
    garden: Optional[bool] = None
    garden_size_sqm: Optional[float] = None
    parking: Optional[str] = None
    parking_price: Optional[float] = None
    cellar: Optional[bool] = None
    storage: Optional[bool] = None
    kitchen_type: Optional[str] = None
    furnished: Optional[bool] = None
    barrier_free: Optional[bool] = None

    # Energy data
    energy_rating: Optional[str] = None
    hwb_value: Optional[float] = None
    fgee_value: Optional[float] = None
    heating_type: Optional[str] = None

    # Regulatory information
    mrg_applicable: Optional[bool] = None
    rent_control_type: Optional[str] = None
    max_rent_controlled: Optional[float] = None
    commission_free: Optional[bool] = None
    commission_percent: Optional[float] = None

    # Investment metrics (calculated)
    estimated_rent: Optional[float] = None
    gross_yield: Optional[float] = None
    net_yield: Optional[float] = None
    cash_flow_monthly: Optional[float] = None
    investment_score: Optional[float] = None
    recommendation: Optional[str] = None

    # Analysis results
    positive_factors: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    analysis_notes: Optional[str] = None

    # LLM-generated summary (optional)
    llm_summary: Optional[str] = None
    llm_summary_generated_at: Optional[datetime] = None

    # Raw data for debugging
    raw_json_ld: Optional[Dict[str, Any]] = None
    raw_html_excerpt: Optional[str] = None

    def calculate_price_per_sqm(self) -> Optional[float]:
        """Calculate price per square meter."""
        if self.price and self.size_sqm and self.size_sqm > 0:
            self.price_per_sqm = round(self.price / self.size_sqm, 2)
            return self.price_per_sqm
        return None

    def calculate_betriebskosten_per_sqm(self) -> Optional[float]:
        """Calculate operating costs per square meter."""
        if self.betriebskosten_monthly and self.size_sqm and self.size_sqm > 0:
            self.betriebskosten_per_sqm = round(
                self.betriebskosten_monthly / self.size_sqm, 2
            )
            return self.betriebskosten_per_sqm
        return None

    def calculate_gross_yield(self) -> Optional[float]:
        """Calculate gross rental yield percentage."""
        if self.estimated_rent and self.price and self.price > 0:
            annual_rent = self.estimated_rent * 12
            self.gross_yield = round((annual_rent / self.price) * 100, 2)
            return self.gross_yield
        return None

    def calculate_net_yield(self) -> Optional[float]:
        """Calculate net rental yield after operating costs."""
        if self.estimated_rent and self.price and self.price > 0:
            monthly_costs = self.betriebskosten_monthly or 0
            net_monthly = self.estimated_rent - monthly_costs
            annual_net = net_monthly * 12
            self.net_yield = round((annual_net / self.price) * 100, 2)
            return self.net_yield
        return None

    def calculate_total_acquisition_cost(
        self,
        include_broker: bool = True,
        broker_percent: float = 3.0,
    ) -> Optional[float]:
        """
        Calculate total acquisition cost including all transaction fees.

        Austrian transaction costs:
        - Grunderwerbsteuer (property transfer tax): 3.5%
        - Grundbucheintragung (land registry): 1.1%
        - Notarkosten (notary): ~1%
        - Maklergebühr (broker): up to 3% (if applicable)
        """
        if not self.price:
            return None

        total = self.price
        # Fixed transaction costs
        total += self.price * (TRANSACTION_COSTS["grunderwerbsteuer"] / 100)
        total += self.price * (TRANSACTION_COSTS["grundbuch"] / 100)
        total += self.price * (TRANSACTION_COSTS["notar"] / 100)

        # Optional broker fee
        if include_broker and not self.commission_free:
            broker = (
                self.commission_percent if self.commission_percent else broker_percent
            )
            total += self.price * (broker / 100)

        return round(total, 2)

    def estimate_monthly_rent(
        self,
        rent_per_sqm: Optional[float] = None,
    ) -> Optional[float]:
        """
        Estimate monthly rent based on location and size.

        Uses district-specific multipliers for Vienna, or regional defaults.
        """
        if not self.size_sqm:
            return None

        # Determine base rent per sqm
        if rent_per_sqm:
            base_rent = rent_per_sqm
        elif self.city and self.city.lower() == "wien":
            # Vienna: use inner/outer distinction
            if self.district_number and self.district_number <= 9:
                base_rent = RENT_PER_SQM_DEFAULTS["vienna_inner"]
            else:
                base_rent = RENT_PER_SQM_DEFAULTS["vienna_outer"]
        elif self.city:
            # Try to find city-specific rate
            city_key = self.city.lower().replace(" ", "_")
            base_rent = RENT_PER_SQM_DEFAULTS.get(
                city_key, RENT_PER_SQM_DEFAULTS["default"]
            )
        else:
            base_rent = RENT_PER_SQM_DEFAULTS["default"]

        # Apply Vienna district multiplier if applicable
        if self.district_number and self.district_number in VIENNA_DISTRICTS:
            multiplier = VIENNA_DISTRICTS[self.district_number]["multiplier"]
            base_rent *= multiplier

        self.estimated_rent = round(base_rent * self.size_sqm, 2)
        return self.estimated_rent

    def calculate_cash_flow(
        self,
        mortgage_rate: float = 3.5,
        down_payment_percent: float = 30,
        loan_term_years: int = 25,
    ) -> Optional[float]:
        """
        Calculate monthly cash flow after mortgage payment.

        Args:
            mortgage_rate: Annual interest rate as percentage
            down_payment_percent: Down payment as percentage of price
            loan_term_years: Loan term in years
        """
        if not self.estimated_rent or not self.price:
            return None

        # Calculate loan amount
        loan_amount = self.price * (1 - down_payment_percent / 100)

        # Monthly mortgage payment (annuity formula)
        if mortgage_rate > 0:
            monthly_rate = mortgage_rate / 100 / 12
            num_payments = loan_term_years * 12
            mortgage_payment = (
                loan_amount
                * (monthly_rate * (1 + monthly_rate) ** num_payments)
                / ((1 + monthly_rate) ** num_payments - 1)
            )
        else:
            mortgage_payment = loan_amount / (loan_term_years * 12)

        # Monthly costs
        operating_costs = self.betriebskosten_monthly or 0

        # Cash flow = rent - mortgage - operating costs
        self.cash_flow_monthly = round(
            self.estimated_rent - mortgage_payment - operating_costs, 2
        )
        return self.cash_flow_monthly

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, list):
                    result[key] = value if value else None
                else:
                    result[key] = value
        return {k: v for k, v in result.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApartmentListing":
        """Create instance from dictionary."""
        # Handle datetime conversion
        if "scraped_at" in data and isinstance(data["scraped_at"], str):
            data["scraped_at"] = datetime.fromisoformat(data["scraped_at"])

        # Filter to only valid fields
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        return cls(**filtered_data)
