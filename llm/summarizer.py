"""LLM-based investment summary generation using Ollama."""

import logging
import re
from typing import Optional

import httpx

from models.apartment import ApartmentListing

logger = logging.getLogger(__name__)


class ApartmentSummarizer:
    """Generates German investment summaries for apartments using Ollama LLM."""

    DEFAULT_MODEL = "qwen3:8b"
    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_TIMEOUT = 120.0  # INCREASED from 60s to 120s
    MAX_RETRIES = 2
    DEFAULT_MAX_WORDS = 150
    DEFAULT_MIN_WORDS = 80  # NEW: Configurable minimum

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_words: int = DEFAULT_MAX_WORDS,
        min_words: int = DEFAULT_MIN_WORDS,  # NEW parameter
    ):
        """
        Initialize the apartment summarizer.

        Args:
            model: Ollama model name to use
            base_url: Ollama API base URL
            timeout: Request timeout in seconds
            max_words: Maximum words for summary
            min_words: Minimum words for summary (default: 80)
        """
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_words = max_words
        self.min_words = min_words  # NEW: Store min words
        self._available: Optional[bool] = None

    async def _check_ollama_availability(self) -> bool:
        """
        Check if Ollama is available and the model is loaded.

        Returns:
            True if Ollama is available, False otherwise
        """
        if self._available is not None:
            return self._available

        logger.info(f"Checking Ollama availability for summarizer at {self.base_url}...")
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(5.0, connect=5.0)
            ) as client:
                # Check if Ollama is running
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code != 200:
                    logger.warning("Ollama not responding for summarizer")
                    self._available = False
                    return False

                # Check if model is available
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                model_base = self.model.split(":")[0]

                if not any(model_base in m for m in models):
                    logger.warning(
                        f"Summarizer model {self.model} not found. Available: {models}"
                    )
                    self._available = False
                    return False

                logger.info(f"Ollama summarizer is available with model {self.model}")
                self._available = True
                return True

        except httpx.ConnectError:
            logger.info("Cannot connect to Ollama for summarizer. Is it running?")
            self._available = False
            return False
        except Exception as e:
            logger.info(f"Error checking Ollama availability for summarizer: {e}")
            self._available = False
            return False

    async def generate_summary(self, apartment: ApartmentListing) -> Optional[str]:
        """
        Generate German investment summary for an apartment.

        Args:
            apartment: Apartment with completed investment analysis

        Returns:
            German summary text (100-150 words) or None if generation fails
        """
        # Check availability first
        if not await self._check_ollama_availability():
            logger.info("Ollama not available, skipping summary generation")
            return None

        logger.info(f"Generating LLM summary for apartment {apartment.listing_id}")

        # Build prompt
        prompt = self._build_summary_prompt(apartment)

        # Make request with retries
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.debug(f"Summary generation attempt {attempt + 1}/{self.MAX_RETRIES}")
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(self.timeout, connect=15.0, pool=5.0)  # INCREASED connect from 10s to 15s
                ) as client:
                    response = await client.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "temperature": 0.3,  # Slightly creative but consistent
                                "num_predict": 250,  # ~150 words + buffer
                            },
                        },
                    )

                    if response.status_code == 200:
                        result = response.json()
                        text = result.get("response", "")
                        summary = self._parse_summary_response(text)
                        if summary:
                            logger.info(
                                f"Summary generated successfully ({len(summary)} chars, "
                                f"{len(summary.split())} words)"
                            )
                            return summary
                        else:
                            logger.warning(
                                f"Failed to parse summary response on attempt {attempt + 1}"
                            )

                    logger.warning(
                        f"Ollama summary request failed (attempt {attempt + 1}/{self.MAX_RETRIES}): "
                        f"status={response.status_code}"
                    )

            except httpx.TimeoutException as e:
                logger.warning(
                    f"Ollama timeout on summary attempt {attempt + 1}/{self.MAX_RETRIES} "
                    f"(timeout: {self.timeout}s): {e}"
                )
            except httpx.ConnectError as e:
                logger.warning(
                    f"Cannot connect to Ollama on summary attempt {attempt + 1}/{self.MAX_RETRIES}: {e}"
                )
            except Exception as e:
                logger.warning(
                    f"Ollama error on summary attempt {attempt + 1}/{self.MAX_RETRIES}: {e}"
                )

        # Return None if all retries failed
        logger.warning(
            f"Summary generation failed after {self.MAX_RETRIES} attempts"
        )
        return None

    def _build_summary_prompt(self, apartment: ApartmentListing) -> str:
        """Build the summary generation prompt for the LLM."""
        # Format financial data
        price_str = f"€{apartment.price:,.0f}" if apartment.price else "n/a"
        size_str = f"{apartment.size_sqm:.0f}m²" if apartment.size_sqm else "n/a"
        yield_str = f"{apartment.gross_yield:.1f}%" if apartment.gross_yield else "n/a"
        cashflow_str = (
            f"€{apartment.cash_flow_monthly:,.0f}/Monat"
            if apartment.cash_flow_monthly
            else "n/a"
        )
        score_str = (
            f"{apartment.investment_score:.1f}/10"
            if apartment.investment_score
            else "n/a"
        )

        # Format location
        location_parts = []
        if apartment.city:
            location_parts.append(apartment.city)
        if apartment.district:
            location_parts.append(apartment.district)
        location_str = ", ".join(location_parts) if location_parts else "n/a"

        # Format positive factors (top 3)
        positive_str = "\n".join(
            f"- {factor}" for factor in apartment.positive_factors[:3]
        )
        if not positive_str:
            positive_str = "- Keine spezifischen positiven Faktoren identifiziert"

        # Format risk factors (top 3)
        risk_str = "\n".join(f"- {factor}" for factor in apartment.risk_factors[:3])
        if not risk_str:
            risk_str = "- Keine signifikanten Risikofaktoren identifiziert"

        return f"""Du bist ein Experte für Immobilieninvestitionen in Österreich.

Analysiere folgende Wohnung und erstelle eine prägnante Investitionszusammenfassung auf Deutsch (100-150 Wörter):

BASISDATEN:
- Titel: {apartment.title or "n/a"}
- Lage: {location_str}
- Größe: {size_str}
- Preis: {price_str}

FINANZIELLE KENNZAHLEN:
- Bruttorendite: {yield_str}
- Monatlicher Cashflow: {cashflow_str}
- Investitionsscore: {score_str}

POSITIVE FAKTOREN:
{positive_str}

RISIKOFAKTOREN:
{risk_str}

EMPFEHLUNG: {apartment.recommendation or "n/a"}

Erstelle eine prägnante Zusammenfassung, die:
1. Die wichtigsten Investmentaspekte hervorhebt
2. Chancen und Risiken ausgewogen darstellt
3. Eine klare Perspektive zur Investitionsentscheidung gibt
4. 100-150 Wörter auf Deutsch umfasst
5. Professionell und objektiv formuliert ist

Antworte NUR mit der Zusammenfassung, ohne zusätzliche Erklärungen oder Formatierung.

Zusammenfassung:"""

    def _parse_summary_response(self, text: str) -> Optional[str]:
        """
        Parse and clean the summary text from LLM response.

        Args:
            text: Raw response text from LLM

        Returns:
            Cleaned summary text or None if invalid
        """
        if not text:
            return None

        # Clean up the text
        summary = text.strip()

        # Remove common prefixes/suffixes
        prefixes_to_remove = [
            "Zusammenfassung:",
            "Summary:",
            "Hier ist die Zusammenfassung:",
            "Analyse:",
        ]
        for prefix in prefixes_to_remove:
            if summary.startswith(prefix):
                summary = summary[len(prefix) :].strip()

        # Remove markdown formatting
        summary = re.sub(r'\*\*([^*]+)\*\*', r'\1', summary)  # Bold
        summary = re.sub(r'\*([^*]+)\*', r'\1', summary)  # Italic
        summary = re.sub(r'`([^`]+)`', r'\1', summary)  # Code

        # Remove extra whitespace
        summary = re.sub(r'\s+', ' ', summary)
        summary = summary.strip()

        # Check word count (keep short summaries, just log warning)
        word_count = len(summary.split())
        if word_count < self.min_words:
            logger.debug(
                f"Summary short ({word_count} words < {self.min_words} minimum), "
                f"but keeping it (target: {self.max_words} words)"
            )
            # CHANGED: Keep short summaries instead of rejecting them

        # Truncate if too long
        if word_count > self.max_words:
            logger.debug(
                f"Truncating summary from {word_count} words to {self.max_words}"
            )
            summary = self._truncate_to_words(summary, self.max_words)

        return summary

    def _truncate_to_words(self, text: str, max_words: int) -> str:
        """
        Truncate text to maximum number of words.

        Args:
            text: Text to truncate
            max_words: Maximum number of words

        Returns:
            Truncated text with ellipsis if needed
        """
        words = text.split()
        if len(words) <= max_words:
            return text

        # Truncate at sentence boundary if possible
        truncated = " ".join(words[:max_words])

        # Find last sentence boundary
        last_period = truncated.rfind(".")
        last_exclamation = truncated.rfind("!")
        last_question = truncated.rfind("?")
        last_sentence_end = max(last_period, last_exclamation, last_question)

        if last_sentence_end > len(truncated) * 0.7:  # If > 70% through, use it
            return truncated[: last_sentence_end + 1]
        else:
            # Otherwise just truncate and add ellipsis
            return truncated + "..."
