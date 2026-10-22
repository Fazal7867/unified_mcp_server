"""
PDF Worker - Enhanced with PyMuPDF native repair capabilities.
This module is MCP-agnostic and contains pure business logic.

IMPROVEMENTS:
- Removed unnecessary pikepdf dependency (PyMuPDF has built-in repair)
- Added doc.is_repaired flag checking
- Integrated fitz.TOOLS.mupdf_warnings() for diagnostics
- Added page-level error tracking
- Added quality metrics (text density, empty pages)
- Enhanced error handling with detailed diagnostics
- Added extract_summary method for metadata-only extraction
"""

from pathlib import Path
from typing import Dict, Tuple, Optional, List
from datetime import datetime

import fitz  # PyMuPDF

from utils.logging_config import get_logger

logger = get_logger("pdf_worker")


class PDFExtractor:
    """
    Enhanced PDF text extraction with security and native repair capabilities.

    Strategy:
    - Single extraction engine: PyMuPDF (fitz)
    - Automatic repair: PyMuPDF repairs during fitz.open()
    - Error detection: Uses doc.is_repaired and mupdf_warnings()
    - Quality metrics: Text density, empty page detection
    """

    def __init__(self):
        """Initialize PDF extractor with security settings."""
        self.allowed_dirs = [
            Path.home() / "Desktop",
            Path.home() / "Documents",
            Path.home() / "Downloads",
        ]
        self.max_pages = 100
        self.max_size_mb = 10

        logger.info(
            f"PDFExtractor initialized. "
            f"Allowed directories: {self.allowed_dirs}, "
            f"Max pages: {self.max_pages}, "
            f"Max size: {self.max_size_mb}MB"
        )

    def _is_path_allowed(self, path: Path) -> Tuple[bool, str]:
        """
        Validate that the file path is within allowed directories.

        Args:
            path: Path to validate

        Returns:
            Tuple of (is_allowed, error_message)
        """
        try:
            resolved_path = path.resolve()

            for allowed_dir in self.allowed_dirs:
                try:
                    resolved_path.relative_to(allowed_dir)
                    return True, ""
                except ValueError:
                    continue

            allowed_list = ", ".join(str(d) for d in self.allowed_dirs)
            return False, f"Access denied. File must be in: {allowed_list}"

        except Exception as e:
            return False, f"Path validation error: {str(e)}"

    def _extract_with_pymupdf(self, path: Path) -> Tuple[str, List[str]]:
        """
        Extract text from PDF using PyMuPDF.

        Args:
            path: Path to PDF file

        Returns:
            Tuple of (extracted_text, list_of_page_errors)

        Raises:
            ValueError: If document validation fails
            fitz.FileDataError: If PDF is severely corrupted
        """
        fitz.TOOLS.reset_mupdf_warnings()
        doc = fitz.open(str(path))

        if doc.page_count == 0:
            doc.close()
            raise ValueError("PDF has no pages - file is severely corrupted")

        if doc.page_count > self.max_pages:
            doc.close()
            raise ValueError(
                f"Too many pages: {doc.page_count} (maximum: {self.max_pages})"
            )

        pages_text: List[str] = []
        extraction_errors: List[str] = []

        for page_num in range(doc.page_count):
            try:
                page = doc[page_num]
                text = page.get_text()

                if text.strip():
                    pages_text.append(
                        f"=== Page {page_num + 1} ===\n{text}"
                    )
                else:
                    extraction_errors.append(
                        f"Page {page_num + 1} has no extractable text "
                        "(may be image-based or blank)"
                    )
                    logger.warning(f"Empty page detected: page {page_num + 1}")

            except Exception as e:
                error_msg = f"Page {page_num + 1}: {str(e)}"
                extraction_errors.append(error_msg)
                logger.error(f"Error extracting {error_msg}")

        full_text = "\n\n".join(pages_text)
        doc.close()

        return full_text, extraction_errors

    def extract(self, pdf_path: str) -> Dict:
        """
        Extract complete text and metadata from PDF file.

        Args:
            pdf_path: Absolute path to PDF file

        Returns:
            Dictionary with keys:
            - success: bool
            - text: str
            - metadata: dict
            - error: str
        """
        try:
            path = Path(pdf_path)

            # STEP 1: Security & File Validation
            is_allowed, error_msg = self._is_path_allowed(path)
            if not is_allowed:
                logger.warning(f"Access denied: {pdf_path}")
                return self._error_response(f"🔒 Security: {error_msg}")

            if not path.exists():
                return self._error_response(f"File not found: {pdf_path}")

            if path.suffix.lower() != ".pdf":
                return self._error_response(f"Not a PDF file: {pdf_path}")

            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > self.max_size_mb:
                return self._error_response(
                    f"PDF too large: {size_mb:.1f}MB (maximum: {self.max_size_mb}MB)"
                )

            logger.info(f"Starting extraction: {path.name} ({size_mb:.2f}MB)")

            # STEP 2: Extract Text
            try:
                full_text, extraction_errors = self._extract_with_pymupdf(path)
            except ValueError as e:
                return self._error_response(str(e))
            except fitz.FileDataError as e:
                return self._error_response(
                    f"Severe PDF corruption: {str(e)}",
                    warnings=fitz.TOOLS.mupdf_warnings(),
                )

            # STEP 3: Diagnostics
            fitz.TOOLS.reset_mupdf_warnings()
            doc = fitz.open(str(path))

            was_repaired = doc.is_repaired
            repair_warnings = fitz.TOOLS.mupdf_warnings()

            page_count = doc.page_count
            doc.close()

            # STEP 4: Quality Metrics
            word_count = len(full_text.split())
            char_count = len(full_text)
            text_density = char_count / page_count if page_count > 0 else 0
            empty_pages = len(extraction_errors)
            needs_ocr = text_density < 100

            # STEP 5: Build Response
            metadata = {
                "filename": path.name,
                "file_size_mb": round(size_mb, 2),
                "pages": page_count,
                "word_count": word_count,
                "char_count": char_count,
                "text_density": round(text_density, 2),
                "extraction_engine": "pymupdf",
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "was_repaired": was_repaired,
                "repair_warnings": repair_warnings or None,
                "extraction_errors": extraction_errors or None,
                "empty_pages": empty_pages,
                "needs_ocr": needs_ocr,
                "quality_score": self._calculate_quality_score(
                    text_density, empty_pages, page_count
                ),
            }

            logger.info(
                f"✓ Extracted {char_count} chars from {path.name} "
                f"(Quality: {metadata['quality_score']:.1f}%, "
                f"Repaired: {was_repaired})"
            )

            return {
                "success": True,
                "text": full_text,
                "metadata": metadata,
                "error": "",
            }

        except Exception as e:
            logger.error(f"Unexpected error during extraction: {e}", exc_info=True)
            return self._error_response(
                f"Extraction error: {str(e)}",
                warnings=fitz.TOOLS.mupdf_warnings(),
            )

    def extract_summary(self, pdf_path: str) -> Dict:
        """
        Quick metadata extraction without full text.

        Args:
            pdf_path: Absolute path to PDF file

        Returns:
            Dictionary with keys:
            - success: bool
            - metadata: dict
            - error: str
        """
        try:
            path = Path(pdf_path)

            is_allowed, error_msg = self._is_path_allowed(path)
            if not is_allowed:
                return self._error_response(f"🔒 Security: {error_msg}")

            if not path.exists():
                return self._error_response(f"File not found: {pdf_path}")

            if path.suffix.lower() != ".pdf":
                return self._error_response(f"Not a PDF file: {pdf_path}")

            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > self.max_size_mb:
                return self._error_response(
                    f"PDF too large: {size_mb:.1f}MB (maximum: {self.max_size_mb}MB)"
                )

            fitz.TOOLS.reset_mupdf_warnings()
            doc = fitz.open(str(path))

            metadata = {
                "filename": path.name,
                "file_size_mb": round(size_mb, 2),
                "pages": doc.page_count,
                "title": doc.metadata.get("title"),
                "author": doc.metadata.get("author"),
                "subject": doc.metadata.get("subject"),
                "keywords": doc.metadata.get("keywords"),
                "creator": doc.metadata.get("creator"),
                "producer": doc.metadata.get("producer"),
                "creation_date": doc.metadata.get("creationDate"),
                "modification_date": doc.metadata.get("modDate"),
                "was_repaired": doc.is_repaired,
                "repair_warnings": fitz.TOOLS.mupdf_warnings() or None,
                "extraction_timestamp": datetime.utcnow().isoformat(),
            }

            doc.close()

            return {
                "success": True,
                "metadata": metadata,
                "error": "",
            }

        except Exception as e:
            logger.error(f"Summary extraction failed: {e}", exc_info=True)
            return self._error_response(
                f"Metadata extraction failed: {str(e)}",
                warnings=fitz.TOOLS.mupdf_warnings(),
            )

    def _calculate_quality_score(
        self,
        text_density: float,
        empty_pages: int,
        total_pages: int,
    ) -> float:
        """
        Calculate a quality score (0–100) for the extraction.
        """
        density_score = min(text_density / 20, 50)
        empty_ratio = empty_pages / max(total_pages, 1)
        empty_score = 50 * (1 - empty_ratio)
        return density_score + empty_score

    def _error_response(
        self,
        error: str,
        warnings: Optional[str] = None,
    ) -> Dict:
        """
        Create standardized error response.
        """
        return {
            "success": False,
            "error": error,
            "text": "",
            "metadata": {
                "mupdf_warnings": warnings if warnings else None,
            },
        }
