"""LLM-based extraction using Ollama."""

import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class OllamaExtractor:
    """Extractor using Ollama for structured data extraction from HTML."""

    DEFAULT_MODEL = "qwen3:8b"
    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_TIMEOUT = 120.0
    MAX_RETRIES = 3

    # Fields to extract via LLM
    EXTRACTION_FIELDS = [
        "title",
        "price",
        "size_sqm",
        "rooms",
        "bedrooms",
        "bathrooms",
        "floor",
        "year_built",
        "condition",
        "building_type",
        "energy_rating",
        "hwb_value",
        "heating_type",
        "betriebskosten_monthly",
        "reparaturrucklage",
        "elevator",
        "balcony",
        "terrace",
        "garden",
        "parking",
        "cellar",
        "commission_free",
        "address",
        "description_summary",
    ]

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        diagnostic_logging: bool = False,
        html_max_chars: int = 50000,
    ):
        """
        Initialize the Ollama extractor.

        Args:
            model: Ollama model name to use
            base_url: Ollama API base URL
            timeout: Request timeout in seconds
            diagnostic_logging: Enable diagnostic logging of raw LLM responses
            html_max_chars: Maximum HTML characters to send to LLM
        """
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.diagnostic_logging = diagnostic_logging
        self.html_max_chars = html_max_chars
        self._available: Optional[bool] = None

    async def check_availability(self) -> bool:
        """
        Check if Ollama is available and the model is loaded.

        Returns:
            True if Ollama is available, False otherwise
        """
        logger.info(f"Checking Ollama availability at {self.base_url}...")
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(5.0, connect=5.0)
            ) as client:
                # Check if Ollama is running
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code != 200:
                    logger.warning("Ollama not responding")
                    self._available = False
                    return False

                # Check if model is available
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                model_base = self.model.split(":")[0]

                if not any(model_base in m for m in models):
                    logger.warning(f"Model {self.model} not found. Available: {models}")
                    self._available = False
                    return False

                logger.info(f"Ollama is available with model {self.model}")
                self._available = True
                return True

        except httpx.ConnectError:
            logger.warning("Cannot connect to Ollama. Is it running?")
            self._available = False
            return False
        except Exception as e:
            logger.warning(f"Error checking Ollama availability: {e}")
            self._available = False
            return False

    async def extract_structured_data(
        self,
        html_content: str,
        existing_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Extract structured apartment data from HTML using LLM.

        Args:
            html_content: Raw HTML content of the apartment page
            existing_data: Already extracted data to supplement

        Returns:
            Dictionary of extracted fields
        """
        # Check availability first
        if self._available is None:
            await self.check_availability()

        if not self._available:
            logger.info("Ollama not available, skipping LLM extraction")
            return existing_data or {}

        logger.info(f"Starting LLM extraction using model {self.model}")

        # Preprocess HTML (remove scripts, collapse whitespace, truncate)
        html_content = self._preprocess_html(html_content)

        # Build prompt
        prompt = self._build_extraction_prompt(html_content, existing_data)

        # Make request with retries
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(f"LLM extraction attempt {attempt + 1}/{self.MAX_RETRIES}")
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(self.timeout, connect=10.0, pool=5.0)
                ) as client:
                    response = await client.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "stream": False,
                            "format": "json",
                            "options": {
                                "temperature": 0.1,
                                "num_predict": 2000,
                            },
                        },
                    )

                    if response.status_code == 200:
                        result = response.json()
                        text = result.get("response", "")
                        extracted = self._parse_json_response(text)
                        if extracted:
                            logger.info(
                                f"LLM extraction successful on attempt {attempt + 1}"
                            )
                            return self._validate_and_clean(extracted, existing_data)
                        else:
                            logger.warning(
                                f"Failed to parse LLM response on attempt {attempt + 1}"
                            )

                    logger.warning(
                        f"Ollama request failed (attempt {attempt + 1}/{self.MAX_RETRIES}): "
                        f"status={response.status_code}"
                    )

            except httpx.TimeoutException as e:
                logger.warning(
                    f"Ollama timeout on attempt {attempt + 1}/{self.MAX_RETRIES} "
                    f"(timeout: {self.timeout}s): {e}"
                )
            except httpx.ConnectError as e:
                logger.warning(
                    f"Cannot connect to Ollama on attempt {attempt + 1}/{self.MAX_RETRIES}: {e}"
                )
            except Exception as e:
                logger.warning(
                    f"Ollama error on attempt {attempt + 1}/{self.MAX_RETRIES}: {e}"
                )

        # Return existing data if all retries failed
        logger.warning(
            f"LLM extraction failed after {self.MAX_RETRIES} attempts, "
            f"returning existing data"
        )
        return existing_data or {}

    def _build_extraction_prompt(
        self,
        html_content: str,
        existing_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build the extraction prompt for the LLM."""
        existing_str = ""
        if existing_data:
            existing_str = f"""
Already extracted data (verify and supplement):
{json.dumps(existing_data, indent=2, ensure_ascii=False)}
"""

        return f"""You are an expert at extracting real estate data from Austrian apartment listings.

Extract information from this willhaben.at apartment listing HTML.
Return ONLY valid JSON with the extracted fields. Use null for missing values.
{existing_str}
GERMAN TERMINOLOGY GUIDE (look for these terms in the HTML):
- Betriebskosten, BK, Monatl. Kosten = betriebskosten_monthly
- Reparaturrücklage, Reparaturfonds, Instandhaltungsrücklage = reparaturrucklage
- Zimmer, Zi., Räume = rooms
- Schlafzimmer, Schlafräume = bedrooms
- Badezimmer, Bad, WC = bathrooms
- Aufzug, Lift, Personenaufzug = elevator
- Stock, Stockwerk, Etage, OG (Obergeschoss), EG (Erdgeschoss) = floor
- Balkon = balcony
- Terrasse = terrace
- Garten, Gartenbenützung = garden
- Parkplatz, Tiefgarage, Garage, Stellplatz, Carport = parking
- Keller, Kellerabteil, Abstellraum = cellar
- Baujahr, Errichtungsjahr = year_built
- HWB, Heizwärmebedarf = hwb_value
- Erstbezug, Saniert, Neuwertig, Gut, Sehr gut, Renovierungsbedürftig = condition
- Altbau, Neubau, Gründerzeit = building_type

PRIORITY FIELDS TO EXTRACT (in order of importance):

**CRITICAL FINANCIAL FIELDS** (highest priority - look in tables, specifications, cost breakdowns):
- betriebskosten_monthly: Monthly operating costs in EUR (number). Look for "Betriebskosten", "Nebenkosten", "BK", "NK", "monatliche Kosten"
  IMPORTANT: Typical range is €50-500/month. Values under €20 are likely placeholders or errors - mark as null if found.
- reparaturrucklage: Monthly repair fund contribution in EUR (number). Look for "Reparaturrücklage", "Instandhaltungsrücklage"
  IMPORTANT: Typical range is €10-200/month. Very low values (< €5) are likely errors - mark as null.
- price: Purchase price in EUR (number, no currency symbol). Usually prominent, labeled "Preis", "Kaufpreis"

**PROPERTY FEATURES** (second priority):
- bedrooms: Number of bedrooms (integer). Look for "Schlafzimmer", may be in room breakdown
- bathrooms: Number of bathrooms (integer). Look for "Badezimmer", "Bad", "WC"
- elevator: Has elevator (boolean). Look for "Aufzug", "Lift"
- balcony: Has balcony (boolean). Look for "Balkon" in features or description
- terrace: Has terrace (boolean). Look for "Terrasse"
- garden: Has garden access (boolean). Look for "Garten", "Gartenbenützung"
- parking: Parking type (one of: tiefgarage, garage, stellplatz, carport, null). Look for "Parkplatz", "Tiefgarage", "Garage"
- cellar: Has cellar storage (boolean). Look for "Keller", "Kellerabteil"
- commission_free: Is commission-free (boolean). Look for "Provisionsfrei", "keine Provision"

**ADDRESS & OTHER FIELDS**:
- address: Full address string. Look for "Adresse", street name with postal code
- title: Listing title (string)
- size_sqm: Living area in square meters (number). Look for "Wohnfläche", "m²", "Quadratmeter"
- rooms: Number of rooms (number, can be decimal like 2.5). Look for "Zimmer", "Zi."
- floor: Floor number (integer, 0 for ground floor). Look for "Stock", "Etage", "EG" (0), "1. OG" (1)
- year_built: Year constructed (integer). Look for "Baujahr"
- condition: Property condition (one of: erstbezug, saniert, renovierungsbedurftig, gut, sehr_gut, neuwertig)
- building_type: Building type (one of: altbau, neubau, grunderzeit)
- energy_rating: Energy class (A++ to G). Look for "Energieausweis", "HWB-Klasse"
- hwb_value: HWB energy value in kWh/m²a (number). Look for "HWB", "Heizwärmebedarf"
- heating_type: Heating type (one of: fernwarme, gas, zentralheizung, fussbodenheizung, elektro, warmepumpe)
- description_summary: Brief 1-2 sentence summary of key selling points

WHERE TO FIND DATA:
- Financial data: Usually in tables with headers "Kosten", "Betriebskosten", specifications section
- Features: Look in feature lists (often bullet points), amenities section, property details table
- Numeric values: Often in structured tables with labels and values in adjacent cells
- Boolean features: If mentioned anywhere in listing = true, otherwise = null

HTML content:
{html_content}

Return only the JSON object, no explanation:"""

    def _parse_json_response(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON from LLM response with enhanced error recovery.

        Strategies (in order):
        1. Direct JSON parse
        2. Extract from markdown code block
        3. Extract JSON object from text
        4. Attempt repair of common malformed JSON
        5. Extract key-value pairs with regex fallback
        """
        if not text:
            return None

        # Log raw response in diagnostic mode
        if self.diagnostic_logging:
            logger.debug(f"LLM raw response ({len(text)} chars): {text[:500]}...")

        # Strategy 1: Direct parse
        try:
            result = json.loads(text)
            if self.diagnostic_logging:
                logger.debug("JSON parsed directly (strategy 1)")
            return result
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from markdown code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                if self.diagnostic_logging:
                    logger.debug("JSON parsed from code block (strategy 2)")
                return result
            except json.JSONDecodeError:
                pass

        # Strategy 3: Extract JSON object from text
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                result = json.loads(json_match.group(0))
                if self.diagnostic_logging:
                    logger.debug("JSON parsed from object extraction (strategy 3)")
                return result
            except json.JSONDecodeError:
                extracted = json_match.group(0)

                # Strategy 4: Attempt repairs
                if self.diagnostic_logging:
                    logger.debug("Attempting JSON repair (strategy 4)...")

                # Fix missing quotes around keys
                repaired = re.sub(r'(\{|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', extracted)
                # Remove trailing commas
                repaired = re.sub(r',(\s*[}\]])', r'\1', repaired)
                # Replace single quotes with double quotes
                repaired = repaired.replace("'", '"')

                try:
                    result = json.loads(repaired)
                    if self.diagnostic_logging:
                        logger.debug("JSON repaired successfully (strategy 4)")
                    return result
                except json.JSONDecodeError:
                    pass

        # Strategy 5: Regex fallback for key-value pairs
        if self.diagnostic_logging:
            logger.debug("Attempting regex key-value extraction (strategy 5)...")

        result = {}
        patterns = [
            (r'"([^"]+)"\s*:\s*"([^"]*)"', str),
            (r'"([^"]+)"\s*:\s*(\d+\.?\d*)', float),
            (r'"([^"]+)"\s*:\s*(true|false)', lambda x: x.lower() == 'true'),
            (r'"([^"]+)"\s*:\s*null', lambda x: None),
        ]

        for pattern, converter in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                key = match.group(1)
                value_str = match.group(2) if len(match.groups()) > 1 else None
                try:
                    if converter == str:
                        result[key] = value_str
                    elif value_str:
                        result[key] = converter(value_str)
                    else:
                        result[key] = None
                except (ValueError, TypeError):
                    continue

        if result:
            if self.diagnostic_logging:
                logger.debug(f"Extracted {len(result)} fields via regex (strategy 5)")
            return result

        logger.warning(f"Could not parse JSON from LLM response. Response: {text[:200]}...")
        if self.diagnostic_logging:
            logger.debug(f"Full failed response: {text}")

        return None

    def _preprocess_html(self, html: str) -> str:
        """
        Preprocess HTML before sending to LLM.

        - Removes script tags (except application/ld+json)
        - Strips excessive whitespace
        - Truncates to configured limit

        Returns:
            Cleaned HTML string
        """
        # First, protect JSON-LD scripts with placeholders
        json_ld_scripts = []
        def save_json_ld(match):
            json_ld_scripts.append(match.group(0))
            return f"___JSON_LD_PLACEHOLDER_{len(json_ld_scripts)-1}___"

        html = re.sub(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>.*?</script>',
            save_json_ld,
            html,
            flags=re.DOTALL | re.IGNORECASE
        )

        # Remove all other script tags
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Restore JSON-LD scripts
        for idx, script in enumerate(json_ld_scripts):
            html = html.replace(f"___JSON_LD_PLACEHOLDER_{idx}___", script)

        # Remove style tags
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Collapse excessive whitespace
        html = re.sub(r'\s+', ' ', html)
        html = re.sub(r'>\s+<', '><', html)

        # Truncate to limit
        if len(html) > self.html_max_chars:
            if self.diagnostic_logging:
                logger.debug(
                    f"HTML truncated: {len(html)} → {self.html_max_chars} chars "
                    f"({(self.html_max_chars/len(html)*100):.1f}% retained)"
                )
            return html[:self.html_max_chars] + "\n... [truncated]"

        return html

    def _validate_and_clean(
        self,
        extracted: Dict[str, Any],
        existing: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validate and clean extracted data, merging with existing."""
        result = dict(existing) if existing else {}
        validated_count = 0
        rejected_count = 0
        rejected_fields = []

        # Type validation and cleaning
        type_validators = {
            "price": (float, lambda x: x > 0),
            "size_sqm": (float, lambda x: 0 < x < 1000),
            "rooms": (float, lambda x: 0 < x < 20),
            "bedrooms": (int, lambda x: 0 <= x < 20),
            "bathrooms": (int, lambda x: 0 <= x < 10),
            "floor": (int, lambda x: -2 <= x < 100),
            "year_built": (int, lambda x: 1800 <= x <= 2030),
            "hwb_value": (float, lambda x: 0 < x < 500),
            "betriebskosten_monthly": (float, lambda x: 10 <= x < 2000),  # Relaxed: Min €10/month
            "reparaturrucklage": (float, lambda x: 1 <= x < 500),  # Relaxed: Min €1/month
        }

        boolean_fields = [
            "elevator",
            "balcony",
            "terrace",
            "garden",
            "cellar",
            "commission_free",
        ]

        string_fields = [
            "title",
            "condition",
            "building_type",
            "energy_rating",
            "heating_type",
            "parking",
            "address",
            "description_summary",
        ]

        # Process numeric fields
        for field, (expected_type, validator) in type_validators.items():
            if field in extracted and extracted[field] is not None:
                try:
                    value = expected_type(extracted[field])
                    if validator(value):
                        result[field] = value
                        validated_count += 1
                        logger.debug(f"Validated {field}={value}")
                    else:
                        rejected_count += 1
                        # Enhanced logging with specific reasons
                        reason = "out of range"
                        if field == "betriebskosten_monthly" and value < 10:
                            reason = f"suspiciously low (€{value} < €10, verify manually)"
                        elif field == "reparaturrucklage" and value < 1:
                            reason = f"suspiciously low (€{value} < €1, verify manually)"
                        rejected_fields.append(f"{field}={extracted[field]} ({reason})")
                        logger.warning(f"Rejected {field}={extracted[field]} ({reason})")
                except (ValueError, TypeError) as e:
                    rejected_count += 1
                    rejected_fields.append(f"{field}={extracted[field]} (type error)")
                    logger.debug(f"Rejected {field}={extracted[field]} (type error: {e})")

        # Process boolean fields
        for field in boolean_fields:
            if field in extracted and extracted[field] is not None:
                if isinstance(extracted[field], bool):
                    result[field] = extracted[field]
                    validated_count += 1
                    logger.debug(f"Validated {field}={extracted[field]}")
                elif isinstance(extracted[field], str):
                    parsed_value = extracted[field].lower() in ("true", "yes", "ja", "1")
                    result[field] = parsed_value
                    validated_count += 1
                    logger.debug(f"Validated {field}={parsed_value} (parsed from '{extracted[field]}')")
                else:
                    rejected_count += 1
                    rejected_fields.append(f"{field}={extracted[field]} (invalid boolean)")
                    logger.debug(f"Rejected {field}={extracted[field]} (invalid boolean type)")

        # Process string fields
        for field in string_fields:
            if field in extracted and extracted[field]:
                if isinstance(extracted[field], str):
                    value = extracted[field].strip()
                    if value and value.lower() not in ("null", "none", "n/a"):
                        result[field] = value
                        validated_count += 1
                        logger.debug(f"Validated {field}='{value[:50]}...'")
                    else:
                        rejected_count += 1
                        rejected_fields.append(f"{field}='{value}' (null-like)")
                        logger.debug(f"Rejected {field}='{value}' (null-like value)")
                else:
                    rejected_count += 1
                    rejected_fields.append(f"{field} (not a string)")
                    logger.debug(f"Rejected {field} (not a string)")

        # Summary logging
        total_fields = validated_count + rejected_count
        if total_fields > 0:
            logger.info(
                f"Validation complete: {validated_count} validated, {rejected_count} rejected "
                f"({validated_count*100//total_fields}% success rate)"
            )
            if rejected_fields:
                logger.debug(f"Rejected fields: {', '.join(rejected_fields[:5])}")

        return result
