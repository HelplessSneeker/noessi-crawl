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
        """Build enhanced extraction prompt with few-shot examples."""
        existing_str = ""
        if existing_data:
            existing_str = f"""
Already extracted data (VERIFY these values - they may be wrong!):
{json.dumps(existing_data, indent=2, ensure_ascii=False)}

IMPORTANT: If existing values seem suspicious (e.g., betriebskosten_monthly < €30, bedrooms=0 for multi-room apartment),
extract the correct value from HTML. Your values will replace bad existing data.
"""

        return f"""You are an expert at extracting real estate data from Austrian apartment listings.

Extract information from this willhaben.at apartment listing HTML.
Return ONLY valid JSON with the extracted fields. Use null for missing values.
{existing_str}

=== FEW-SHOT EXAMPLES ===

Example 1 - Financial fields in table:
HTML: <td>Betriebskosten</td><td>EUR 145,00</td>
JSON: {{"betriebskosten_monthly": 145.0}}

Example 2 - Multiple costs:
HTML: <td>Betriebskosten</td><td>EUR 120,50</td><td>Reparaturrücklage</td><td>EUR 35,00</td>
JSON: {{"betriebskosten_monthly": 120.5, "reparaturrucklage": 35.0}}

Example 3 - Room breakdown:
HTML: 3 Zimmer (2 Schlafzimmer, 1 Bad)
JSON: {{"rooms": 3, "bedrooms": 2, "bathrooms": 1}}

Example 4 - Features in list:
HTML: <li>Aufzug</li><li>Balkon</li><li>Tiefgarage</li>
JSON: {{"elevator": true, "balcony": true, "parking": "tiefgarage"}}

Example 5 - Floor and year:
HTML: 3. Stock, Baujahr 1985
JSON: {{"floor": 3, "year_built": 1985}}

Example 6 - Energy data:
HTML: HWB: 65,2 kWh/m²a, Energieeffizienzklasse: B
JSON: {{"hwb_value": 65.2, "energy_rating": "B"}}

=== GERMAN TERMINOLOGY GUIDE ===

CRITICAL FINANCIAL FIELDS (look in cost tables, "Kosten" sections):
- "Betriebskosten", "BK", "Nebenkosten", "NK" → betriebskosten_monthly
  * Typical: €50-500/month
  * Values < €30 are ERRORS - look harder for real value

- "Reparaturrücklage", "Reparaturfonds" → reparaturrucklage
  * Typical: €20-200/month
  * Values < €10 are suspicious

Property specs:
- "Zimmer" → rooms (can be decimal: 2.5)
- "Schlafzimmer" → bedrooms (integer)
- "Badezimmer", "Bad" → bathrooms (integer)
- "Stock", "EG" (=0), "1. OG" (=1) → floor

Features:
- "Aufzug" → elevator
- "Balkon" → balcony
- "Parkplatz", "Tiefgarage" → parking

=== VALIDATION RULES ===

Before returning JSON, validate:
- betriebskosten_monthly: 30-2000 (if < 30, likely error)
- reparaturrucklage: 10-500
- size_sqm: 10-1000
- rooms: 1-20
- bedrooms: 0-10
- bathrooms: 1-10
- floor: -2 to 20
- year_built: 1700-2030
- hwb_value: 5-1000

=== HTML CONTENT ===

{html_content}

Return only the JSON object with these fields (use null for missing):
{{"title": "...", "price": 123000, "size_sqm": 45.5, "rooms": 2, ...}}

Return only the JSON, no explanation."""

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
        Preprocess HTML with priority-based truncation.

        Strategy:
        1. Preserve JSON-LD (highest value)
        2. Remove scripts/styles
        3. Preserve property details sections
        4. Smart truncation if needed

        Returns:
            Cleaned HTML string
        """
        # Protect JSON-LD with placeholders
        json_ld_scripts = []
        def save_json_ld(match):
            json_ld_scripts.append(match.group(0))
            return f"___JSON_LD_PLACEHOLDER_{len(json_ld_scripts)-1}___"

        html = re.sub(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>.*?</script>',
            save_json_ld, html, flags=re.DOTALL | re.IGNORECASE
        )

        # Remove scripts/styles
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Collapse whitespace
        html = re.sub(r'\s+', ' ', html)
        html = re.sub(r'>\s+<', '><', html)

        # Restore JSON-LD
        for idx, script in enumerate(json_ld_scripts):
            html = html.replace(f"___JSON_LD_PLACEHOLDER_{idx}___", script)

        # Smart truncation
        if len(html) > self.html_max_chars:
            original_len = len(html)

            # Extract priority sections
            priority_patterns = [
                r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>.*?</script>',
                r'<table[^>]*>.*?</table>',  # Tables often have costs
                r'<div[^>]*class="[^"]*specification[^"]*"[^>]*>.*?</div>',
                r'<div[^>]*class="[^"]*attributes[^"]*"[^>]*>.*?</div>',
                r'<ul[^>]*>.*?</ul>',  # Feature lists
            ]

            priority_content = []
            for pattern in priority_patterns:
                matches = re.findall(pattern, html, flags=re.DOTALL | re.IGNORECASE)
                priority_content.extend(matches)

            priority_html = '\n'.join(priority_content)

            if len(priority_html) <= self.html_max_chars:
                html = priority_html
                if self.diagnostic_logging:
                    logger.info(f"HTML truncation (priority): {original_len} → {len(html)} chars")
            else:
                html = priority_html[:self.html_max_chars]
                if self.diagnostic_logging:
                    logger.info(f"HTML truncation (hard): {original_len} → {len(html)} chars")

            html += "\n... [truncated]"

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
            "size_sqm": (float, lambda x: 10 < x < 1000),  # Tightened: Min 10 m²
            "rooms": (float, lambda x: 0.5 < x < 20),  # Allow 0.5 for studio
            "bedrooms": (int, lambda x: 0 <= x < 20),
            "bathrooms": (int, lambda x: 0 <= x < 10),
            "floor": (int, lambda x: -2 <= x < 25),  # Tightened from 100
            "year_built": (int, lambda x: 1700 <= x <= 2030),  # Expanded from 1800
            "hwb_value": (float, lambda x: 5 < x < 1000),  # Tightened and expanded range
            "betriebskosten_monthly": (float, lambda x: 30 <= x < 2000),  # INCREASED from €10 to €30
            "reparaturrucklage": (float, lambda x: 10 <= x < 500),  # INCREASED from €1 to €10
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
