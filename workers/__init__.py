"""
Workers package - Contains business logic for PDF extraction.
Web scraping is now handled by the ScrapeOrchestrator pipeline (renderer/extractor/postprocessor).

Architecture (CURRENT):
- PDF extraction via PDFExtractor
- Web scraping via core.orchestrator (not workers)
- Dual output (user + analytics) preserved for PDFs
- Security: Path validation, local-only processing
- PDF extraction via PDFExtractor (includes optional OCR fallback)

"""

from .pdf_worker import PDFExtractor

from .schema import (
    ExtractionResult,
    create_pdf_extraction_result,
    save_extraction_with_validation
)

# Re-export only what is still used
__all__ = [
    # PDF
    'PDFExtractor',

    # Schema (PDF)
    'ExtractionResult',
    'create_pdf_extraction_result',
    'save_extraction_with_validation',
]