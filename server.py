"""
Unified MCP Server - Enhanced with production-grade workers.
Combines PDF and Industrial-grade Web extraction tools.
"""
import asyncio
import json
from typing import Any
from datetime import datetime
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from utils.logging_config import setup_logging, get_logger, get_audit_logger
from workers import PDFExtractor

from core import ScrapeOrchestrator
from utils.structured_logger import new_request_id
from utils.result_processor import ScraperResultProcessor



main_logger, audit_logger = setup_logging()
logger = get_logger('server')

app = Server("unified-extractor")

pdf_extractor = PDFExtractor()
orchestrator = ScrapeOrchestrator()
result_processor = ScraperResultProcessor(output_dir="scraping_results")

try:
    result_processor = ScraperResultProcessor(output_dir="scraping_results")
    logger.info(f"✅ Result processor initialized. Output dir: {result_processor.output_dir}")
    logger.info(f"   Content dir: {result_processor.content_dir}")
    logger.info(f"   Analytics dir: {result_processor.analytics_dir}")
except Exception as e:
    logger.error(f"❌ Failed to initialize result processor: {e}")
    result_processor = None


PDF_ANALYTICS_DIR = Path.cwd() / "extracted_content" / "pdf" / "analytics"
PDF_ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

EXTRACTION_OUTPUT_DIR = Path.cwd() / "extracted_content"
EXTRACTION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@app.list_tools()
async def list_tools() -> list[Tool]:
    """Register ALL available tools with MCP client."""
    logger.info("Tools list requested by client")
    
    return [
        Tool(
            name="extract_pdf",
            description=(
                "Extract all text content from a PDF file. "
                "Provide the absolute file path to the PDF. "
                "Returns the extracted text organized by page, plus metadata. "
                "Maximum file size: 10MB. Maximum pages: 100. "
                "Security: Only files in Desktop, Documents, or Downloads folders are accessible."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the PDF file (e.g., C:/Users/YourName/Desktop/document.pdf)"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="extract_pdf_summary",
            description=(
                "Extract PDF metadata and statistics without full text. "
                "Faster than full extraction - useful for indexing or quick previews. "
                "Returns: filename, page count, size, word count, title, author."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the PDF file"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="scrape_url",
            description="Industrial-grade web scraper (auto static/dynamic)",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to scrape"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="view_extracted_json",
            description=(
                "View the contents of a previously saved extraction JSON file. "
                "Use this to read and analyze JSON files created by extraction tools."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the JSON file"
                    }
                },
                "required": ["file_path"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute tool requests from MCP client."""
    logger.info(f"Tool called: {name}")
    
    if name == "extract_pdf":
        return await handle_extract_pdf(arguments)
    elif name == "extract_pdf_summary":
        return await handle_extract_summary(arguments)
    elif name == "scrape_url":
        return await handle_scrape_url(arguments)
    elif name == "view_extracted_json":
        return await handle_view_json(arguments)
    else:
        error_msg = f"Unknown tool: {name}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"❌ Error: {error_msg}")]


async def handle_scrape_url(arguments: dict) -> list[TextContent]:
    """Handle industrial-grade web scraping via orchestrator."""
    url = arguments.get("url")
    
    audit_logger.info(
        f"TOOL_CALL | tool=scrape_url | url={url} | "
        f"timestamp={datetime.now().isoformat()}"
    )
    
    if not url:
        return [TextContent(type="text", text="❌ Error: URL is required")]
    
    request_id = new_request_id()
    result = await orchestrator.scrape(url, request_id)
    
    # Save results to disk with comprehensive error handling
    file_info = None
    
    if result_processor is None:
        file_info = "\n⚠️  Warning: Result processor not initialized - files not saved\n"
        logger.warning("Result processor is None - cannot save files")
    else:
        try:
            logger.info(f"Attempting to save results for URL: {url}")
            file_paths = result_processor.save_results(url, result)
            result['saved_files'] = file_paths
            
            file_info = f"""
📁 **FILES SAVED SUCCESSFULLY**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 Content File:
   {file_paths['content_file']}

📊 Analytics File:
   {file_paths['analytics_file']}

🕒 Saved At:
   {file_paths['timestamp']}

💾 Location:
   All files are in: scraping_results/
   - Content files: scraping_results/content/
   - Analytics files: scraping_results/analytics/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            logger.info(f"✅ Successfully saved files: {file_paths}")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"❌ Failed to save scraping results: {e}\n{error_details}")
            
            file_info = f"""
⚠️  **WARNING: Failed to Save Files**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Error: {str(e)}

The scraping succeeded but results were not saved to disk.
Check server logs for detailed error trace.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # Format comprehensive response
    response_text = f"""✅ Web Scraping Complete
{file_info}

{'='*60}
SCRAPING RESULT DATA:
{'='*60}

{json.dumps(result, indent=2)}

{'='*60}
"""
    
    return [TextContent(type="text", text=response_text)]

async def handle_extract_pdf(arguments: dict) -> list[TextContent]:
    """Handle full PDF text extraction with enhanced quality metrics."""
    file_path = arguments.get("file_path")
    
    audit_logger.info(
        f"TOOL_CALL | tool=extract_pdf | file={file_path} | "
        f"timestamp={datetime.now().isoformat()}"
    )
    
    if not file_path:
        return [TextContent(type="text", text="❌ Error: file_path parameter is required")]
    
    result = pdf_extractor.extract(file_path)
    
    if not result['success']:
        mupdf_warnings = result.get('metadata', {}).get('mupdf_warnings')
        warnings_text = f"\n\n🔧 Technical Details:\n{mupdf_warnings}" if mupdf_warnings else ""
        
        return [TextContent(
            type="text",
            text=f"""❌ PDF Extraction Failed

Error: {result['error']}{warnings_text}

💡 Troubleshooting:
- Ensure file path is absolute
- Check file exists and is readable
- Verify file is a valid PDF
- Maximum size: 10MB, Maximum pages: 100
"""
        )]
    
    metadata = result['metadata']
    quality_score = metadata.get('quality_score', 0)
    quality_stars = "⭐" * int(quality_score / 20)
    needs_ocr = metadata.get('needs_ocr', False)
    ocr_notice = "\n⚠️  Low text density - document may be image-based (OCR recommended)" if needs_ocr else ""
    
    repair_status = ""
    if metadata.get('was_repaired'):
        repair_status = "\n🔧 PDF was automatically repaired during extraction"
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_name = Path(metadata['filename']).stem
    analytics_filename = f"{pdf_name}_{timestamp}.json"
    analytics_path = PDF_ANALYTICS_DIR / analytics_filename
    
    analytics_data = {
        "extracted_at": datetime.now().isoformat(),
        "file_path": file_path,
        "metadata": {
            "filename": metadata['filename'],
            "pages": metadata['pages'],
            "size_mb": metadata['file_size_mb'],
            "char_count": metadata['char_count'],
            "word_count": metadata['word_count'],
            "text_density": metadata.get('text_density', 0),
            "empty_pages": metadata.get('empty_pages', 0),
            "quality_score": quality_score,
            "needs_ocr": needs_ocr,
            "was_repaired": metadata.get('was_repaired', False)
        },
        "extraction": {
            "success": True,
            "text_length": len(result['text']),
            "processing_type": "local",
            "extraction_engine": metadata['extraction_engine']
        }
    }
    
    with open(analytics_path, 'w', encoding='utf-8') as f:
        json.dump(analytics_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved PDF analytics to: {analytics_path}")
    
    response_text = f"""✅ PDF Extraction Successful

📄 File: {metadata['filename']}
📊 Pages: {metadata['pages']}
💾 Size: {metadata['file_size_mb']} MB

📈 Total Characters: {metadata['char_count']:,}
📖 Estimated Words: {metadata['word_count']:,}

✨ Quality Score: {quality_score:.1f}/100 {quality_stars}
⚙️  Extraction Engine: {metadata['extraction_engine']}{repair_status}{ocr_notice}

{result['text']}

📊 Analytics saved to: `{analytics_path}`
"""
    
    return [TextContent(type="text", text=response_text)]


async def handle_extract_summary(arguments: dict) -> list[TextContent]:
    """Handle quick metadata-only extraction."""
    file_path = arguments.get("file_path")
    
    audit_logger.info(
        f"TOOL_CALL | tool=extract_pdf_summary | file={file_path} | "
        f"timestamp={datetime.now().isoformat()}"
    )
    
    if not file_path:
        return [TextContent(type="text", text="❌ Error: file_path parameter is required")]
    
    if hasattr(pdf_extractor, 'extract_summary'):
        result = pdf_extractor.extract_summary(file_path)
    else:
        result = pdf_extractor.extract(file_path)
    
    if not result['success']:
        return [TextContent(type="text", text=f"❌ Error: {result['error']}")]
    
    metadata = result['metadata']
    
    summary = f"""📄 PDF Quick Summary

📁 Filename: {metadata['filename']}
📊 Pages: {metadata['pages']}
💾 File Size: {metadata['file_size_mb']} MB
📖 Word Count: ~{metadata.get('word_count', 'N/A'):,}
📝 Title: {metadata.get('title', 'N/A')}
✏️  Author: {metadata.get('author', 'N/A')}
"""
    
    return [TextContent(type="text", text=summary)]


async def handle_view_json(arguments: dict) -> list[TextContent]:
    """Handle viewing saved JSON extraction files."""
    file_path = arguments.get("file_path")
    
    audit_logger.info(
        f"TOOL_CALL | tool=view_extracted_json | file={file_path} | "
        f"timestamp={datetime.now().isoformat()}"
    )
    
    if not file_path:
        return [TextContent(type="text", text="❌ Error: file_path parameter is required")]
    
    try:
        json_path = Path(file_path).resolve()
        expected_parent = EXTRACTION_OUTPUT_DIR.resolve()
        
        if not str(json_path).startswith(str(expected_parent)):
            return [TextContent(type="text", text="❌ Security Error: File must be inside extracted_content directory")]
        
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        formatted_json = json.dumps(json_data, indent=2, ensure_ascii=False)
        
        return [TextContent(type="text", text=formatted_json)]
    
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error Reading File\n\n{str(e)}")]


async def main():
    """Run the unified MCP server via stdio transport."""
    logger.info("=" * 60)
    logger.info("UNIFIED MCP SERVER STARTING (SCRAPE_URL ENABLED)")
    logger.info("=" * 60)
    logger.info(f"Server Name: {app.name}")
    logger.info(f"Total Tools: 4 (2 PDF + 1 Web + 1 Utility)")
    logger.info("Architecture: Orchestrator-based web scraping")
    logger.info("Security: Path validation + robots.txt + audit logging")
    logger.info("Utility: JSON file viewer for saved extractions")
    logger.info("=" * 60)
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())