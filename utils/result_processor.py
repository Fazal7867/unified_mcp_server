"""
Scraper Result Processor
Handles cleaning, structuring, and saving scraping results to disk.
Creates two files per scrape: content.json and analytics.json
"""
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class ScraperResultProcessor:
    """Process and save web scraping results in structured format."""
    
    def __init__(self, output_dir: str = "scraping_results"):
        """
        Initialize the result processor.
        
        Args:
            output_dir: Directory to save results (default: "scraping_results")
        """
        # Use absolute path to avoid confusion
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organization
        self.content_dir = self.output_dir / "content"
        self.analytics_dir = self.output_dir / "analytics"
        self.content_dir.mkdir(exist_ok=True)
        self.analytics_dir.mkdir(exist_ok=True)
        
        # Log the absolute paths for debugging
        print("Scraping results will be saved to:")
        print(f"   Root: {self.output_dir}")
        print(f"   Content: {self.content_dir}")
        print(f"   Analytics: {self.analytics_dir}")
    
    def clean_text(self, text: Optional[str]) -> str:
        """
        Remove excessive whitespace and normalize text.
        """
        if not text:
            return ""
        
        text = ' '.join(text.split())
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n\n'.join(lines)
        return text
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            domain = url.replace('https://', '').replace('http://', '')
            domain = domain.split('/')[0]
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return "unknown_domain"
    
    def extract_structured_content(self, url: str, scrape_result: Dict[str, Any]) -> Dict[str, Any]:
        content = scrape_result.get('content', {})
        quality = scrape_result.get('quality', {})
        
        main_text = content.get('text', '')
        blocks = self._process_blocks(content.get('blocks', []))
        
        structured = {
            "metadata": {
                "url": url,
                "domain": self.extract_domain(url),
                "scraped_at": datetime.utcnow().isoformat() + 'Z',
                "scrape_success": scrape_result.get('success', False)
            },
            "content": {
                "main_text": self.clean_text(main_text),
                "blocks": blocks,
                "statistics": {
                    "total_characters": len(main_text),
                    "total_words": len(main_text.split()) if main_text else 0,
                    "block_count": len(blocks)
                }
            },
            "quality_metrics": {
                "word_count": quality.get('word_count', 0),
                "paragraph_count": quality.get('paragraph_count', 0),
                "quality_score": quality.get('quality_score', 0)
            }
        }
        
        return structured
    
    def _process_blocks(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        processed = []
        
        for idx, block in enumerate(blocks):
            try:
                block_type = block.get('type', 'unknown')
                block_text = self.clean_text(block.get('text', ''))
                
                if block_text:
                    processed.append({
                        "block_id": idx + 1,
                        "type": block_type,
                        "text": block_text,
                        "word_count": len(block_text.split())
                    })
            except Exception as e:
                print(f"Warning: Skipped malformed block {idx}: {e}")
                continue
        
        return processed
    
    def extract_analytics(self, url: str, scrape_result: Dict[str, Any]) -> Dict[str, Any]:
        quality = scrape_result.get('quality', {})
        diagnostics = scrape_result.get('diagnostics', {})
        
        analytics = {
            "metadata": {
                "url": url,
                "domain": self.extract_domain(url),
                "scraped_at": datetime.utcnow().isoformat() + 'Z',
                "scrape_id": self._generate_scrape_id(url)
            },
            "extraction_quality": {
                "quality_score": quality.get('quality_score', 0),
                "word_count": quality.get('word_count', 0),
                "paragraph_count": quality.get('paragraph_count', 0),
                "quality_assessment": self._assess_quality(quality.get('quality_score', 0))
            },
            "diagnostics": {
                "success": scrape_result.get('success', False),
                "request_id": diagnostics.get('request_id', ''),
                "failure_reason": diagnostics.get('failure_reason'),
                "extractor": diagnostics.get('extractor', ''),
                "probe_mode": diagnostics.get('probe_mode', ''),
                "fallback_used": diagnostics.get('fallback_used', False)
            },
            "performance": {
                "extraction_engine": diagnostics.get('extractor', 'unknown'),
                "content_blocks_extracted": len(scrape_result.get('content', {}).get('blocks', []))
            }
        }
        
        if not scrape_result.get('success', False):
            analytics['failure_details'] = {
                "reason": diagnostics.get('failure_reason', 'unknown'),
                "error_message": scrape_result.get('error', 'No error message provided')
            }
        
        return analytics
    
    def _assess_quality(self, quality_score: float) -> str:
        if quality_score >= 0.8:
            return "Excellent"
        elif quality_score >= 0.5:
            return "Good"
        elif quality_score >= 0.3:
            return "Fair"
        elif quality_score >= 0.1:
            return "Poor"
        else:
            return "Very Poor"
    
    def _generate_scrape_id(self, url: str) -> str:
        timestamp = datetime.utcnow().isoformat()
        hash_input = f"{url}_{timestamp}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    def save_results(self, url: str, scrape_result: Dict[str, Any]) -> Dict[str, str]:
        try:
            safe_filename = self._generate_safe_filename(url)
            
            content_data = self.extract_structured_content(url, scrape_result)
            analytics_data = self.extract_analytics(url, scrape_result)
            
            content_path = self.content_dir / f"{safe_filename}_content.json"
            with open(content_path, 'w', encoding='utf-8') as f:
                json.dump(content_data, f, indent=2, ensure_ascii=False)
            
            analytics_path = self.analytics_dir / f"{safe_filename}_analytics.json"
            with open(analytics_path, 'w', encoding='utf-8') as f:
                json.dump(analytics_data, f, indent=2, ensure_ascii=False)
            
            print("Saved files:")
            print(f"   Content: {content_path}")
            print(f"   Analytics: {analytics_path}")
            
            return {
                "content_file": str(content_path),
                "analytics_file": str(analytics_path),
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }
            
        except Exception as e:
            print(f"Error saving results: {e}")
            raise
    
    def _generate_safe_filename(self, url: str) -> str:
        safe = url.replace('https://', '').replace('http://', '')
        
        special_chars = ['/', '?', '&', '=', '#', '%', ':', '.']
        for char in special_chars:
            safe = safe.replace(char, '_')
        
        while '__' in safe:
            safe = safe.replace('__', '_')
        
        safe = safe.strip('_')
        safe = safe[:150]
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return f"{safe}_{timestamp}"