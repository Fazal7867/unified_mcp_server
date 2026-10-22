"""
FastAPI Gateway for MCP Server

Purpose:
- Expose existing MCP tool workflows via HTTP
- Reuse MCP workers WITHOUT duplicating logic
- Act as a human / system-facing access layer

This gateway does NOT replace MCP.
Claude continues to interact with MCP directly via stdio.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime

from workers.pdf_worker import PDFExtractor
from core.orchestrator import ScrapeOrchestrator
from utils.structured_logger import new_request_id
from utils.logging_config import get_logger

# -------------------------------------------------------------------
# App Initialization
# -------------------------------------------------------------------

app = FastAPI(
    title="MCP Gateway API",
    description="HTTP Gateway over MCP tool workflows",
    version="0.1.0",
)

logger = get_logger("fastapi-gateway")

# Initialize shared MCP components
pdf_extractor = PDFExtractor()
scrape_orchestrator = ScrapeOrchestrator()

# -------------------------------------------------------------------
# Request Models
# -------------------------------------------------------------------

class PDFExtractRequest(BaseModel):
    file_path: str = Field(
        ...,
        description="Absolute path to the PDF file (must be in allowed directories)"
    )


class URLScrapeRequest(BaseModel):
    url: str = Field(
        ...,
        description="URL to scrape"
    )


@app.get("/")
def root():
    return {
        "service": "MCP FastAPI Gateway",
        "description": "Gateway layer exposing MCP tool workflows",
        "endpoints": ["/health", "/docs", "/pdf/extract", "/web/scrape"]
    }

# -------------------------------------------------------------------
# Health Check
# -------------------------------------------------------------------

@app.get("/health")
def health_check():
    """
    Basic health endpoint for monitoring and demos
    """
    return {
        "status": "ok",
        "service": "mcp-fastapi-gateway",
        "timestamp": datetime.utcnow().isoformat()
    }

# -------------------------------------------------------------------
# PDF Extraction Endpoint
# -------------------------------------------------------------------

@app.post("/pdf/extract")
def extract_pdf(request: PDFExtractRequest):
    """
    Extract full text and metadata from a PDF.

    Internally calls the same PDFExtractor used by MCP tools.
    """
    logger.info(f"PDF extraction requested: {request.file_path}")

    result = pdf_extractor.extract(request.file_path)

    outcome = result.get("metadata", {}).get("outcome")

    if outcome == "FAILED_TECHNICAL":
        logger.error(f"PDF extraction technical failure: {result.get('error')}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": result.get("error"),
                "diagnostics": result.get("metadata", {})
        }
    )

    return {
        "success": True,
        "data": result,
        "processed_at": datetime.utcnow().isoformat()
    }

# -------------------------------------------------------------------
# PDF Summary Endpoint
# -------------------------------------------------------------------

@app.post("/pdf/summary")
def extract_pdf_summary(request: PDFExtractRequest):
    """
    Extract metadata-only summary from a PDF.
    Faster than full extraction.
    """
    logger.info(f"PDF summary requested: {request.file_path}")

    result = pdf_extractor.extract_summary(request.file_path)

    if not result.get("success"):
        logger.error(f"PDF summary failed: {result.get('error')}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": result.get("error"),
                "diagnostics": result.get("metadata", {})
            }
        )

    return {
        "success": True,
        "data": result,
        "processed_at": datetime.utcnow().isoformat()
    }

# -------------------------------------------------------------------
# Web Scraping Endpoint
# -------------------------------------------------------------------

@app.post("/web/scrape")
async def scrape_url(request: URLScrapeRequest):
    """
    Scrape and extract main content from a URL.

    Uses the same industrial-grade ScrapeOrchestrator
    that is exposed as an MCP tool.
    """
    request_id = new_request_id()
    logger.info(f"Web scrape requested: {request.url} | request_id={request_id}")

    result = await scrape_orchestrator.scrape(request.url, request_id)

    if not result.get("success"):
        logger.error(
            f"Web scrape failed | request_id={request_id} | "
            f"reason={result.get('diagnostics', {}).get('failure_reason')}"
        )
        raise HTTPException(
            status_code=400,
            detail=result
        )

    return {
        "success": True,
        "request_id": request_id,
        "data": result,
        "processed_at": datetime.utcnow().isoformat()
    }
