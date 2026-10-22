"""
Standard Schema Module - Industry-grade JSON schema with validation.

This module provides standardized data models for all extraction types (PDF, static web, dynamic web).
It ensures consistent output format, enables validation, and supports database integration.

Usage:
    # Wrap existing extraction results in standard schema
    from workers.schema import create_pdf_extraction_result, create_web_extraction_result
    
    # PDF extraction
    pdf_result = pdf_extractor.extract(file_path)
    standard_result = create_pdf_extraction_result(pdf_result, execution_time_ms=200)
    standard_result.save(output_dir)
    
    # Web extraction
    webpage = web_extractor.extract(url)
    standard_result = create_web_extraction_result(webpage, execution_time_ms=500)
    standard_result.save(output_dir)

Benefits:
    ✓ Consistent JSON structure across all extraction types
    ✓ Built-in validation
    ✓ Versioning support (schema_version)
    ✓ Quality metrics (confidence_score, completeness_score)
    ✓ Database-ready format
    ✓ JSONL support for batch processing
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
import uuid

# ============================================================================
# ENUMS
# ============================================================================

class ExtractionStatus(Enum):
    """Standardized status codes for extraction results."""
    SUCCESS = "success"
    PARTIAL = "partial_success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ExtractionType(Enum):
    """Type of content extraction performed."""
    PDF = "pdf"
    WEB_STATIC = "web_static"
    WEB_DYNAMIC = "web_dynamic"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class StandardMetadata:
    """
    Standardized metadata for all extractions.
    Following industry best practices for data cataloging.
    
    Fields:
        extraction_id: Unique identifier (UUID)
        extraction_type: Type of extraction (PDF/web_static/web_dynamic)
        source_url: Original URL or file path
        extracted_at: ISO 8601 timestamp
        execution_time_ms: Processing time in milliseconds
        status: Extraction status (success/partial/failed/timeout)
        schema_version: Schema version for compatibility tracking
        source_filename: Original filename (if applicable)
        error: Error message if failed
        warnings: List of warning messages
        confidence_score: AI confidence in extraction quality (0-1)
        completeness_score: Percentage of content successfully extracted (0-1)
    """
    # REQUIRED FIELDS (no defaults) - must come first
    extraction_id: str  # UUID
    extraction_type: ExtractionType
    source_url: str
    extracted_at: str  # ISO 8601 timestamp
    execution_time_ms: float
    status: ExtractionStatus
    
    # OPTIONAL FIELDS (with defaults) - must come after required fields
    schema_version: str = "2.0"
    source_filename: Optional[str] = None
    error: Optional[str] = None
    warnings: Optional[List[str]] = None
    confidence_score: Optional[float] = None  # 0-1
    completeness_score: Optional[float] = None  # 0-1


@dataclass
class ExtractionResult:
    """
    Universal extraction result container.
    Can represent PDF, static web, or dynamic web extractions.
    
    This standardized format enables:
    - Consistent data structure across extraction types
    - Database insertion without type-specific logic
    - Validation before storage
    - Versioning for schema evolution
    - Quality tracking via metrics
    
    Example:
        result = ExtractionResult(
            metadata=StandardMetadata(...),
            content={"text": "...", "word_count": 1000},
            structure={"sections": [...], "links": [...]},
            technical={"parser": "lxml", "quality_score": 0.85}
        )
        
        # Validate
        is_valid, errors = result.validate()
        
        # Save
        filepath = result.save(output_dir)
    """
    # Standard metadata (always present)
    metadata: StandardMetadata
    
    # Content (type-specific)
    content: Dict[str, Any]
    
    # Structure (type-specific, optional)
    structure: Optional[Dict[str, Any]] = None
    
    # Technical details (optional)
    technical: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary with proper enum handling.
        
        Returns:
            Dictionary representation with enums converted to strings
        """
        result = asdict(self)
        
        # Convert enums to strings for JSON serialization
        result["metadata"]["extraction_type"] = self.metadata.extraction_type.value
        result["metadata"]["status"] = self.metadata.status.value
        
        return result
    
    def to_json(self, indent: int = 2) -> str:
        """
        Convert to JSON string.
        
        Args:
            indent: Number of spaces for indentation (None for compact)
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def save(self, output_dir: Path, filename: Optional[str] = None) -> Path:
        """
        Save to JSON file with standardized naming.
        
        Args:
            output_dir: Directory to save file
            filename: Custom filename (auto-generated if None)
        
        Returns:
            Path to saved file
        
        Example:
            filepath = result.save(Path("./extracted_content"))
            # Saves to: ./extracted_content/pdf_document_name_20240118_143052.json
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if filename is None:
            # Auto-generate filename: {type}_{source}_{timestamp}.json
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            source_name = self._sanitize_filename(self.metadata.source_url)
            filename = f"{self.metadata.extraction_type.value}_{source_name}_{timestamp}.json"
        
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
        
        return filepath
    
    def save_to_jsonl(self, jsonl_path: Path) -> None:
        """
        Append to JSONL file for streaming/batch processing.
        
        JSONL (JSON Lines) format is ideal for:
        - Streaming large datasets
        - Batch processing
        - Database imports
        - Log aggregation
        
        Args:
            jsonl_path: Path to JSONL file (will be created or appended)
        
        Example:
            result.save_to_jsonl(Path("./extractions.jsonl"))
            # Appends one line: {"metadata": {...}, "content": {...}}
        """
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(jsonl_path, 'a', encoding='utf-8') as f:
            f.write(self.to_json(indent=None) + '\n')
    
    @staticmethod
    def _sanitize_filename(url: str) -> str:
        """
        Convert URL or file path to safe filename.
        
        Args:
            url: URL or file path
        
        Returns:
            Safe filename string (max 50 chars)
        """
        from urllib.parse import urlparse
        
        if url.startswith("file://"):
            # File path
            return Path(url[7:]).stem[:50]
        else:
            # URL
            parsed = urlparse(url)
            safe = parsed.netloc + parsed.path
            safe = safe.replace("/", "_").replace(":", "_").replace(".", "_")
            return safe[:50]  # Limit length
    
    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate extraction result against schema.
        
        Checks:
        - Required fields are present
        - Field types are correct
        - Content structure matches extraction type
        - Quality scores are in valid range (0-1)
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        
        Example:
            is_valid, errors = result.validate()
            if not is_valid:
                print(f"Validation errors: {errors}")
        """
        errors = []
        
        # Check required metadata fields
        if not self.metadata.extraction_id:
            errors.append("Missing extraction_id")
        
        if not self.metadata.source_url:
            errors.append("Missing source_url")
        
        if not self.metadata.extracted_at:
            errors.append("Missing extracted_at timestamp")
        
        # Validate quality scores if present
        if self.metadata.confidence_score is not None:
            if not 0 <= self.metadata.confidence_score <= 1:
                errors.append(f"Invalid confidence_score: {self.metadata.confidence_score} (must be 0-1)")
        
        if self.metadata.completeness_score is not None:
            if not 0 <= self.metadata.completeness_score <= 1:
                errors.append(f"Invalid completeness_score: {self.metadata.completeness_score} (must be 0-1)")
        
        # Validate content structure based on type
        if self.metadata.extraction_type == ExtractionType.PDF:
            required_fields = ["text", "word_count", "pages"]
            for field in required_fields:
                if field not in self.content:
                    errors.append(f"PDF extraction missing '{field}' field in content")
        
        elif self.metadata.extraction_type in [ExtractionType.WEB_STATIC, ExtractionType.WEB_DYNAMIC]:
            required_fields = ["full_text", "title", "word_count"]
            for field in required_fields:
                if field not in self.content:
                    errors.append(f"Web extraction missing '{field}' field in content")
        
        return (len(errors) == 0, errors)


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def create_pdf_extraction_result(
    pdf_data: Dict[str, Any],
    execution_time_ms: float
) -> ExtractionResult:
    """
    Factory function for PDF extraction results.
    Converts raw PDF extraction data to standardized format.
    
    Args:
        pdf_data: Raw PDF extraction result from PDFExtractor.extract()
        execution_time_ms: Time taken for extraction
    
    Returns:
        Standardized ExtractionResult
    
    Example:
        pdf_result = pdf_extractor.extract("document.pdf")
        standard_result = create_pdf_extraction_result(pdf_result, 250.5)
        standard_result.save(output_dir)
    """
    # Build metadata
    metadata = StandardMetadata(
        extraction_id=str(uuid.uuid4()),
        extraction_type=ExtractionType.PDF,
        schema_version="2.0",
        source_url=f"file://{pdf_data['metadata']['filename']}",
        source_filename=pdf_data['metadata']['filename'],
        extracted_at=datetime.now().isoformat(),
        execution_time_ms=execution_time_ms,
        status=ExtractionStatus.SUCCESS if pdf_data['success'] else ExtractionStatus.FAILED,
        error=pdf_data.get('error'),
        warnings=[pdf_data['metadata'].get('repair_warnings')] if pdf_data['metadata'].get('repair_warnings') else None,
        
        # Quality metrics
        confidence_score=pdf_data['metadata'].get('quality_score', 0) / 100 if pdf_data['success'] else None,
        completeness_score=1.0 if pdf_data['success'] else 0.0
    )
    
    # Build content
    content = {
        "text": pdf_data.get('text', ''),
        "word_count": pdf_data['metadata'].get('word_count', 0),
        "char_count": pdf_data['metadata'].get('char_count', 0),
        "pages": pdf_data['metadata'].get('pages', 0)
    }
    
    # Build technical details
    technical = {
        "extraction_engine": pdf_data['metadata'].get('extraction_engine'),
        "file_size_mb": pdf_data['metadata'].get('file_size_mb'),
        "was_repaired": pdf_data['metadata'].get('was_repaired', False),
        "text_density": pdf_data['metadata'].get('text_density'),
        "empty_pages": pdf_data['metadata'].get('empty_pages', 0),
        "needs_ocr": pdf_data['metadata'].get('needs_ocr', False),
        "quality_score": pdf_data['metadata'].get('quality_score')
    }
    
    return ExtractionResult(
        metadata=metadata,
        content=content,
        technical=technical
    )


def create_web_extraction_result(
    webpage: Any,  # WebPage object
    execution_time_ms: float,
    is_dynamic: bool = False
) -> ExtractionResult:
    """
    Factory function for web extraction results.
    Converts WebPage object to standardized format.
    
    Args:
        webpage: WebPage object from web_worker or playwright_worker
        execution_time_ms: Time taken for extraction
        is_dynamic: True if JavaScript rendering was used
    
    Returns:
        Standardized ExtractionResult
    
    Example:
        webpage = web_extractor.extract("https://example.com")
        standard_result = create_web_extraction_result(webpage, 450.2, is_dynamic=False)
        standard_result.save(output_dir)
    """
    # Calculate quality scores
    content_ratio = getattr(webpage, 'main_content_ratio', 0.8)
    confidence = 0.95 if content_ratio > 0.8 else (0.85 if content_ratio > 0.6 else 0.7)
    completeness = content_ratio
    
    # Build metadata
    metadata = StandardMetadata(
        extraction_id=str(uuid.uuid4()),
        extraction_type=ExtractionType.WEB_DYNAMIC if is_dynamic else ExtractionType.WEB_STATIC,
        schema_version="2.0",
        source_url=webpage.url,
        extracted_at=webpage.extracted_at,
        execution_time_ms=execution_time_ms,
        status=ExtractionStatus.SUCCESS,
        confidence_score=confidence,
        completeness_score=completeness
    )
    
    # Build content
    content = {
        "title": webpage.title,
        "description": webpage.description,
        "author": webpage.author,
        "published_date": webpage.published_date,
        "language": webpage.language,
        "full_text": webpage.full_text,
        "main_content_html": webpage.main_content_html,
        "word_count": webpage.word_count,
        "reading_time_minutes": webpage.reading_time_minutes
    }
    
    # Build structure
    structure = {
        "sections": [asdict(s) for s in webpage.sections] if webpage.sections else [],
        "links": [asdict(link) for link in webpage.links] if webpage.links else [],
        "images": [asdict(img) for img in webpage.images] if webpage.images else [],
        "structured_data": webpage.structured_data if hasattr(webpage, 'structured_data') else None
    }
    
    # Build technical details
    technical = {
        "parser_used": webpage.parser_used,
        "status_code": webpage.status_code,
        "content_type": webpage.content_type,
        "response_time_ms": webpage.response_time_ms,
        "main_content_ratio": getattr(webpage, 'main_content_ratio', None),
        "ad_density": getattr(webpage, 'ad_density', None),
        "mobile_friendly": getattr(webpage, 'mobile_friendly', None)
    }
    
    return ExtractionResult(
        metadata=metadata,
        content=content,
        structure=structure,
        technical=technical
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def save_extraction_with_validation(
    result: ExtractionResult,
    output_dir: Path,
    jsonl_path: Optional[Path] = None,
    raise_on_error: bool = False
) -> Optional[Path]:
    """
    Save extraction result with validation.
    
    Args:
        result: ExtractionResult to save
        output_dir: Directory for JSON file
        jsonl_path: Optional JSONL file for appending
        raise_on_error: If True, raise exception on validation errors
    
    Returns:
        Path to saved file, or None if validation failed and raise_on_error=False
    
    Example:
        filepath = save_extraction_with_validation(
            result,
            Path("./extracted_content"),
            jsonl_path=Path("./extractions.jsonl"),
            raise_on_error=True
        )
    """
    # Validate before saving
    is_valid, errors = result.validate()
    
    if not is_valid:
        error_msg = f"Validation errors: {errors}"
        if raise_on_error:
            raise ValueError(error_msg)
        else:
            print(f"⚠️  {error_msg}")
            return None
    
    # Save to JSON
    filepath = result.save(output_dir)
    print(f"✅ Saved: {filepath}")
    
    # Optionally save to JSONL for streaming/batch processing
    if jsonl_path:
        result.save_to_jsonl(jsonl_path)
        print(f"✅ Appended to JSONL: {jsonl_path}")
    
    return filepath


def load_extraction_result(filepath: Path) -> ExtractionResult:
    """
    Load ExtractionResult from JSON file.
    
    Args:
        filepath: Path to JSON file
    
    Returns:
        ExtractionResult object
    
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If JSON is invalid or schema version mismatch
    
    Example:
        result = load_extraction_result(Path("./extracted_content/pdf_doc_20240118.json"))
        print(f"Extracted {result.content['word_count']} words")
    """
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check schema version
    if data['metadata']['schema_version'] != "2.0":
        raise ValueError(f"Unsupported schema version: {data['metadata']['schema_version']}")
    
    # Reconstruct enums
    metadata_dict = data['metadata']
    metadata_dict['extraction_type'] = ExtractionType(metadata_dict['extraction_type'])
    metadata_dict['status'] = ExtractionStatus(metadata_dict['status'])
    
    # Reconstruct StandardMetadata
    metadata = StandardMetadata(**metadata_dict)
    
    return ExtractionResult(
        metadata=metadata,
        content=data['content'],
        structure=data.get('structure'),
        technical=data.get('technical')
    )


# ============================================================================
# BATCH PROCESSING
# ============================================================================

def process_jsonl_batch(jsonl_path: Path, batch_size: int = 100):
    """
    Process JSONL file in batches (generator function).
    Useful for processing large datasets without loading everything into memory.
    
    Args:
        jsonl_path: Path to JSONL file
        batch_size: Number of records per batch
    
    Yields:
        List of ExtractionResult objects (up to batch_size)
    
    Example:
        for batch in process_jsonl_batch(Path("./extractions.jsonl"), batch_size=50):
            # Process 50 records at a time
            for result in batch:
                print(f"Processing {result.metadata.extraction_id}")
    """
    batch = []
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            
            # Reconstruct enums
            metadata_dict = data['metadata']
            metadata_dict['extraction_type'] = ExtractionType(metadata_dict['extraction_type'])
            metadata_dict['status'] = ExtractionStatus(metadata_dict['status'])
            
            metadata = StandardMetadata(**metadata_dict)
            
            result = ExtractionResult(
                metadata=metadata,
                content=data['content'],
                structure=data.get('structure'),
                technical=data.get('technical')
            )
            
            batch.append(result)
            
            if len(batch) >= batch_size:
                yield batch
                batch = []
    
    # Yield remaining records
    if batch:
        yield batch