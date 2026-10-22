"""
Core web scraping pipeline.

Pipeline:
Renderer → Extractor → PostProcessor
Orchestrated by ScrapeOrchestrator.

This package contains:
- orchestrator.py
- renderer.py
- extractor.py
- postprocessor.py
"""

from .orchestrator import ScrapeOrchestrator
from .renderer import StaticRenderer, BrowserRenderer
from .extractor import ContentExtractor
from .postprocessor import PostProcessor

__all__ = [
    "ScrapeOrchestrator",
    "StaticRenderer",
    "BrowserRenderer",
    "ContentExtractor",
    "PostProcessor",
]