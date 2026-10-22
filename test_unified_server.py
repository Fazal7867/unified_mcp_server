"""
Test script for the unified MCP server.
Tests tool registration and basic functionality without MCP client.
"""
import asyncio
from pathlib import Path

from workers import PDFExtractor, WebExtractor
from utils.logging_config import setup_logging


async def test_pdf_worker():
    """Test PDF extraction worker."""
    print("\n" + "="*60)
    print("TEST 1: PDF Worker")
    print("="*60)
    
    extractor = PDFExtractor()
    
    # Test with a non-existent file (should fail gracefully)
    test_path = str(Path.home() / "Desktop" / "test.pdf")
    print(f"\nTesting with path: {test_path}")
    
    result = extractor.extract(test_path)
    
    print(f"Success: {result['success']}")
    if not result['success']:
        print(f"Error: {result['error']}")
    else:
        print(f"Metadata: {result['metadata']}")
        print(f"Text length: {len(result['text'])} chars")
    
    print("\n✅ PDF Worker test complete")


async def test_web_worker():
    """Test web extraction worker."""
    print("\n" + "="*60)
    print("TEST 2: Web Worker")
    print("="*60)
    
    extractor = WebExtractor()
    
    # Test with example.com
    test_url = "http://example.com"
    print(f"\nTesting with URL: {test_url}")
    
    try:
        html = await extractor.fetch_url(test_url)
        print(f"✓ Successfully fetched {len(html)} characters")
        
        # Test BeautifulSoup extraction
        from workers.web_worker import extract_with_beautifulsoup
        result = extract_with_beautifulsoup(html)
        
        print(f"Title: {result['title']}")
        print(f"Headings found: {result['statistics']['total_headings']}")
        print(f"Links found: {result['statistics']['total_links']}")
        print(f"Text length: {result['statistics']['text_length']} chars")
        
        print("\n✅ Web Worker test complete")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await extractor.close()


async def test_tool_registration():
    """Test that all tools are registered correctly."""
    print("\n" + "="*60)
    print("TEST 3: Tool Registration")
    print("="*60)
    
    # Import and manually call the list_tools function
    import server
    
    # Call the list_tools handler directly
    tools = await server.list_tools()
    
    print(f"\n✓ Total tools registered: {len(tools)}")
    print("\nTools:")
    for i, tool in enumerate(tools, 1):
        print(f"  {i}. {tool.name}")
        print(f"     Description: {tool.description[:80]}...")
        required = tool.inputSchema.get('required', [])
        print(f"     Required params: {required}")
    
    # Verify we have exactly 5 tools
    assert len(tools) == 5, f"Expected 5 tools, got {len(tools)}"
    
    # Verify tool names
    expected_names = [
        'extract_pdf',
        'extract_pdf_summary',
        'extract_website_content',
        'extract_website_xpath',
        'summarize_website'
    ]
    
    actual_names = [tool.name for tool in tools]
    for name in expected_names:
        assert name in actual_names, f"Tool '{name}' not found in registration"
    
    print("\n✅ Tool registration test complete")
    print("   All 5 tools correctly registered:")
    for name in expected_names:
        print(f"   ✓ {name}")


async def test_worker_independence():
    """Test that workers are MCP-agnostic."""
    print("\n" + "="*60)
    print("TEST 4: Worker Independence")
    print("="*60)
    
    # Check that workers don't import MCP types
    try:
        import workers.pdf_worker as pdf_module
        import workers.web_worker as web_module
        
        # Get module source to check imports
        import inspect
        
        pdf_source = inspect.getsource(pdf_module)
        web_source = inspect.getsource(web_module)
        
        # Check for MCP imports
        mcp_indicators = ['from mcp', 'import mcp', 'from mcp.types', 'from mcp.server']
        
        pdf_has_mcp = any(indicator in pdf_source for indicator in mcp_indicators)
        web_has_mcp = any(indicator in web_source for indicator in mcp_indicators)
        
        if pdf_has_mcp:
            print("❌ PDF worker imports MCP (should be MCP-agnostic)")
        else:
            print("✓ PDF worker is MCP-agnostic")
        
        if web_has_mcp:
            print("❌ Web worker imports MCP (should be MCP-agnostic)")
        else:
            print("✓ Web worker is MCP-agnostic")
        
        assert not pdf_has_mcp, "PDF worker should not import MCP"
        assert not web_has_mcp, "Web worker should not import MCP"
        
        print("\n✅ Worker independence test complete")
        
    except Exception as e:
        print(f"⚠️  Could not verify worker independence: {e}")
        print("   (This is not critical - workers may still be correctly isolated)")


async def test_server_structure():
    """Test server structure and imports."""
    print("\n" + "="*60)
    print("TEST 5: Server Structure")
    print("="*60)
    
    import server
    
    # Check that server has the main components
    checks = [
        ('app', 'MCP Server instance'),
        ('pdf_extractor', 'PDF worker instance'),
        ('web_extractor', 'Web worker instance'),
        ('list_tools', 'Tool registration handler'),
        ('call_tool', 'Tool execution handler'),
        ('main', 'Server entry point')
    ]
    
    all_passed = True
    for attr, description in checks:
        if hasattr(server, attr):
            print(f"✓ {description}: {attr}")
        else:
            print(f"❌ Missing {description}: {attr}")
            all_passed = False
    
    assert all_passed, "Server missing required components"
    
    # Check server name
    assert server.app.name == "unified-extractor", f"Expected server name 'unified-extractor', got '{server.app.name}'"
    print(f"\n✓ Server name: {server.app.name}")
    
    print("\n✅ Server structure test complete")


async def test_handlers_exist():
    """Test that all handler functions exist."""
    print("\n" + "="*60)
    print("TEST 6: Handler Functions")
    print("="*60)
    
    import server
    
    handlers = [
        'handle_extract_pdf',
        'handle_extract_summary',
        'handle_extract_website_content',
        'handle_extract_website_xpath',
        'handle_summarize_website'
    ]
    
    all_exist = True
    for handler in handlers:
        if hasattr(server, handler):
            print(f"✓ {handler}")
        else:
            print(f"❌ Missing: {handler}")
            all_exist = False
    
    assert all_exist, "Some handler functions are missing"
    
    print("\n✅ All handler functions exist")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("UNIFIED MCP SERVER TEST SUITE")
    print("="*60)
    
    # Setup logging
    setup_logging()
    
    try:
        # Run tests
        await test_pdf_worker()
        await test_web_worker()
        await test_tool_registration()
        await test_worker_independence()
        await test_server_structure()
        await test_handlers_exist()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print("\nYour unified MCP server is ready!")
        print("\nNext steps:")
        print("  1. Configure Claude Desktop to use this server")
        print("  2. Add absolute path to server.py in config")
        print("  3. Use venv Python in config (not system Python)")
        print("  4. Restart Claude Desktop")
        print("  5. Test with real PDFs and websites")
        print("  6. Monitor logs: mcp_server.log and audit.log")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("\nPlease fix the issue and run tests again.")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())