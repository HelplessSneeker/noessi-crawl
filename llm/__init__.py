"""LLM integration modules for extraction and analysis."""

from .analyzer import InvestmentAnalyzer
from .extractor import OllamaExtractor

__all__ = [
    "OllamaExtractor",
    "InvestmentAnalyzer",
]
