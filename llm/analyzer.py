"""Investment analysis for apartment listings."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from models.apartment import ApartmentListing
from models.constants import (
    MRG_BUILDING_CUTOFF_YEAR,
    RECOMMENDATION_THRESHOLDS,
    RENT_PER_SQM_DEFAULTS,
    VIENNA_DISTRICTS,
    VIENNA_PRICE_PER_SQM,
    InvestmentRecommendation,
)

logger = logging.getLogger(__name__)


class InvestmentAnalyzer:
    """Analyzer for apartment investment potential."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the analyzer with configuration.

        Args:
            config: Analysis configuration with mortgage rates, rent estimates, etc.
        """
        self.config = config or {}

        # Analysis parameters with defaults
        self.mortgage_rate = self.config.get("mortgage_rate", 3.5)
        self.down_payment_percent = self.config.get("down_payment_percent", 30)
        self.transaction_cost_percent = self.config.get("transaction_cost_percent", 9)
        self.loan_term_years = self.config.get("loan_term_years", 25)

        # Rent estimates by region
        self.rent_estimates = self.config.get(
            "estimated_rent_per_sqm", RENT_PER_SQM_DEFAULTS
        )

        # Filtering thresholds
        self.min_yield = self.config.get("min_yield", 3.0)
        self.min_score = self.config.get("min_investment_score", 4.0)

    def analyze_apartment(self, apartment: ApartmentListing) -> ApartmentListing:
        """
        Perform full investment analysis on an apartment.

        Args:
            apartment: The apartment listing to analyze

        Returns:
            The apartment with investment metrics populated
        """
        # Calculate derived metrics
        apartment.calculate_price_per_sqm()
        apartment.calculate_betriebskosten_per_sqm()

        # Estimate rent if not provided
        if not apartment.estimated_rent:
            self._estimate_rent(apartment)

        # Calculate yields
        apartment.calculate_gross_yield()
        apartment.calculate_net_yield()

        # Calculate cash flow
        apartment.calculate_cash_flow(
            mortgage_rate=self.mortgage_rate,
            down_payment_percent=self.down_payment_percent,
            loan_term_years=self.loan_term_years,
        )

        # Calculate investment score
        score, positive, risks = self._calculate_score(apartment)
        apartment.investment_score = score
        apartment.positive_factors = positive
        apartment.risk_factors = risks

        # Determine recommendation
        apartment.recommendation = self._get_recommendation(score).value

        return apartment

    def _estimate_rent(self, apartment: ApartmentListing) -> None:
        """Estimate monthly rent based on location and size."""
        if not apartment.size_sqm:
            return

        # Determine base rent per sqm
        if apartment.city and apartment.city.lower() == "wien":
            if apartment.district_number:
                if apartment.district_number <= 9:
                    base_rent = self.rent_estimates.get(
                        "vienna_inner", RENT_PER_SQM_DEFAULTS["vienna_inner"]
                    )
                else:
                    base_rent = self.rent_estimates.get(
                        "vienna_outer", RENT_PER_SQM_DEFAULTS["vienna_outer"]
                    )

                # Apply district multiplier
                if apartment.district_number in VIENNA_DISTRICTS:
                    multiplier = VIENNA_DISTRICTS[apartment.district_number][
                        "multiplier"
                    ]
                    base_rent *= multiplier
            else:
                base_rent = self.rent_estimates.get(
                    "vienna_outer", RENT_PER_SQM_DEFAULTS["vienna_outer"]
                )
        elif apartment.city:
            city_key = apartment.city.lower().replace(" ", "_")
            base_rent = self.rent_estimates.get(
                city_key,
                self.rent_estimates.get("default", RENT_PER_SQM_DEFAULTS["default"]),
            )
        else:
            base_rent = self.rent_estimates.get(
                "default", RENT_PER_SQM_DEFAULTS["default"]
            )

        apartment.estimated_rent = round(base_rent * apartment.size_sqm, 2)

    def _calculate_score(
        self, apartment: ApartmentListing
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculate investment score (0-10 scale).

        Scoring weights are balanced so maximum possible is 10.0:
        - Base score: 5.0
        - Yield bonus: up to +1.5
        - Price vs market: up to +1.0
        - Operating costs: up to +0.5
        - Condition bonus: up to +0.5
        - Energy efficiency: up to +0.5
        - Features bonus: up to +0.5
        - Cash flow bonus: up to +0.5
        - Penalties can reduce score below 5.0

        Returns:
            Tuple of (score, positive_factors, risk_factors)
        """
        score = 5.0  # Base score
        positive_factors: List[str] = []
        risk_factors: List[str] = []

        # === Yield scoring (up to +1.5) ===
        if apartment.gross_yield:
            if apartment.gross_yield >= 5.5:
                score += 1.5
                positive_factors.append(
                    f"Ausgezeichnete Rendite: {apartment.gross_yield:.1f}%"
                )
            elif apartment.gross_yield >= 4.5:
                score += 1.0
                positive_factors.append(f"Gute Rendite: {apartment.gross_yield:.1f}%")
            elif apartment.gross_yield >= 3.5:
                score += 0.5
                positive_factors.append(
                    f"Akzeptable Rendite: {apartment.gross_yield:.1f}%"
                )
            elif apartment.gross_yield < 2.5:
                score -= 1.0
                risk_factors.append(f"Niedrige Rendite: {apartment.gross_yield:.1f}%")

        # === Price vs market (up to +1.0) ===
        if apartment.price_per_sqm and apartment.district_number:
            market_price = VIENNA_PRICE_PER_SQM.get(apartment.district_number)
            if market_price:
                price_ratio = apartment.price_per_sqm / market_price
                if price_ratio < 0.85:
                    score += 1.0
                    positive_factors.append(
                        f"Unter Marktpreis ({price_ratio:.0%} vom Durchschnitt)"
                    )
                elif price_ratio < 0.95:
                    score += 0.5
                    positive_factors.append("Wettbewerbsfähiger Preis")
                elif price_ratio > 1.15:
                    score -= 0.5
                    risk_factors.append(
                        f"Über Marktpreis ({price_ratio:.0%} vom Durchschnitt)"
                    )

        # === Operating costs (up to +0.5) ===
        if apartment.betriebskosten_monthly is None or apartment.betriebskosten_per_sqm is None:
            # Missing critical financial data
            score -= 0.5
            risk_factors.append("Betriebskosten nicht verfügbar - manuelle Prüfung erforderlich")
        elif apartment.betriebskosten_per_sqm:
            if apartment.betriebskosten_per_sqm < 2.0:
                score += 0.5
                positive_factors.append("Niedrige Betriebskosten")
            elif apartment.betriebskosten_per_sqm > 4.0:
                score -= 0.5
                risk_factors.append(
                    f"Hohe Betriebskosten ({apartment.betriebskosten_per_sqm:.2f} EUR/m²)"
                )

        # === Condition (up to +0.5) ===
        if apartment.condition:
            good_conditions = ["erstbezug", "saniert", "neuwertig", "sehr_gut"]
            bad_conditions = ["renovierungsbedurftig"]

            if apartment.condition in good_conditions:
                score += 0.5
                positive_factors.append(f"Guter Zustand: {apartment.condition}")
            elif apartment.condition in bad_conditions:
                score -= 1.0
                risk_factors.append("Renovierung erforderlich")

        # === Energy efficiency (up to +0.5) ===
        if apartment.energy_rating:
            if apartment.energy_rating in ["A++", "A+", "A", "B"]:
                score += 0.5
                positive_factors.append(f"Energieeffizient ({apartment.energy_rating})")
            elif apartment.energy_rating in ["F", "G"]:
                score -= 0.5
                risk_factors.append(
                    f"Schlechte Energieeffizienz ({apartment.energy_rating})"
                )

        # === Features (up to +0.5) ===
        feature_count = sum(
            [
                apartment.elevator or False,
                apartment.balcony or False,
                apartment.terrace or False,
                apartment.garden or False,
                apartment.parking is not None,
                apartment.cellar or False,
            ]
        )
        if feature_count >= 4:
            score += 0.5
            positive_factors.append(
                f"Gut ausgestattet ({feature_count} Ausstattungsmerkmale)"
            )
        elif feature_count == 0:
            risk_factors.append("Keine besonderen Ausstattungsmerkmale")

        # === Cash flow (up to +0.5) ===
        if apartment.cash_flow_monthly is not None:
            if apartment.cash_flow_monthly > 200:
                score += 0.5
                positive_factors.append(
                    f"Positiver Cashflow (+{apartment.cash_flow_monthly:.0f} EUR/Monat)"
                )
            elif apartment.cash_flow_monthly > 0:
                score += 0.25
                positive_factors.append("Leicht positiver Cashflow")
            elif apartment.cash_flow_monthly < -300:
                score -= 0.5
                risk_factors.append(
                    f"Negativer Cashflow ({apartment.cash_flow_monthly:.0f} EUR/Monat)"
                )

        # === MRG risk assessment ===
        if apartment.year_built and apartment.year_built < MRG_BUILDING_CUTOFF_YEAR:
            apartment.mrg_applicable = True
            risk_factors.append("MRG-Mietpreisbindung könnte gelten (Vorkriegsbau)")
            score -= 0.25

        # === Commission consideration ===
        if apartment.commission_free:
            score += 0.25
            positive_factors.append("Provisionsfrei")

        # === Elevator for upper floors ===
        if apartment.floor and apartment.floor >= 3 and not apartment.elevator:
            risk_factors.append("Hohe Etage ohne Aufzug")
            score -= 0.25

        # Clamp score to 0-10 range
        score = max(0.0, min(10.0, round(score, 1)))

        return score, positive_factors, risk_factors

    def _get_recommendation(self, score: float) -> InvestmentRecommendation:
        """Get recommendation based on score."""
        for recommendation, (min_score, max_score) in RECOMMENDATION_THRESHOLDS.items():
            if min_score <= score < max_score:
                return recommendation

        # Default to CONSIDER if score is exactly at boundary
        return InvestmentRecommendation.CONSIDER

    def should_include(
        self,
        apartment: ApartmentListing,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """
        Determine if apartment should be included based on filters.

        Args:
            apartment: The analyzed apartment
            filters: Filter criteria from config

        Returns:
            Tuple of (include, reason)
        """
        if not filters:
            return True, "No filters applied"

        # Price filter
        max_price = filters.get("max_price")
        if max_price and apartment.price and apartment.price > max_price:
            return False, f"Price {apartment.price} exceeds max {max_price}"

        # Size filters
        min_size = filters.get("min_size_sqm")
        max_size = filters.get("max_size_sqm")
        if min_size and apartment.size_sqm and apartment.size_sqm < min_size:
            return False, f"Size {apartment.size_sqm}m2 below minimum {min_size}m2"
        if max_size and apartment.size_sqm and apartment.size_sqm > max_size:
            return False, f"Size {apartment.size_sqm}m2 above maximum {max_size}m2"

        # Yield filter
        min_yield = filters.get("min_yield")
        if min_yield and apartment.gross_yield and apartment.gross_yield < min_yield:
            return False, f"Yield {apartment.gross_yield}% below minimum {min_yield}%"

        # District exclusion
        excluded_districts = filters.get("excluded_districts", [])
        if apartment.district_number in excluded_districts:
            return False, f"District {apartment.district_number} is excluded"

        # Operating costs filter
        max_bk = filters.get("max_betriebskosten_per_sqm")
        if max_bk and apartment.betriebskosten_per_sqm:
            if apartment.betriebskosten_per_sqm > max_bk:
                return (
                    False,
                    f"Operating costs {apartment.betriebskosten_per_sqm} EUR/m2 exceed max",
                )

        # Condition filter
        if (
            filters.get("exclude_renovierung_needed")
            and apartment.condition == "renovierungsbedurftig"
        ):
            return False, "Property needs renovation"

        # Energy filter
        if filters.get("exclude_poor_energy"):
            if apartment.energy_rating in ["F", "G"]:
                return False, f"Poor energy rating: {apartment.energy_rating}"

        # Score filter
        min_score = filters.get("min_investment_score")
        if (
            min_score
            and apartment.investment_score
            and apartment.investment_score < min_score
        ):
            return (
                False,
                f"Score {apartment.investment_score} below minimum {min_score}",
            )

        return True, "Passed all filters"

    def generate_summary(self, apartment: ApartmentListing) -> str:
        """Generate a text summary of the investment analysis."""
        lines = [
            f"Investment Analysis: {apartment.title or 'Apartment'}",
            "-" * 50,
            f"Price: EUR {apartment.price:,.0f}" if apartment.price else "Price: N/A",
            f"Size: {apartment.size_sqm:.0f} m2" if apartment.size_sqm else "Size: N/A",
            f"Price/m2: EUR {apartment.price_per_sqm:,.0f}"
            if apartment.price_per_sqm
            else "",
            "",
            "Investment Metrics:",
            f"  Estimated Rent: EUR {apartment.estimated_rent:,.0f}/month"
            if apartment.estimated_rent
            else "",
            f"  Gross Yield: {apartment.gross_yield:.2f}%"
            if apartment.gross_yield
            else "",
            f"  Net Yield: {apartment.net_yield:.2f}%" if apartment.net_yield else "",
            f"  Cash Flow: EUR {apartment.cash_flow_monthly:,.0f}/month"
            if apartment.cash_flow_monthly
            else "",
            "",
            f"Investment Score: {apartment.investment_score:.1f}/10",
            f"Recommendation: {apartment.recommendation}",
        ]

        if apartment.positive_factors:
            lines.append("")
            lines.append("Positive Factors:")
            for factor in apartment.positive_factors:
                lines.append(f"  + {factor}")

        if apartment.risk_factors:
            lines.append("")
            lines.append("Risk Factors:")
            for factor in apartment.risk_factors:
                lines.append(f"  - {factor}")

        return "\n".join(filter(None, lines))
