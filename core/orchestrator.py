import time
import httpx
from core.renderer import StaticRenderer, BrowserRenderer
from core.extractor import ContentExtractor
from core.postprocessor import PostProcessor
from utils.structured_logger import StructuredLogger
from utils.robots import RobotsChecker
from utils.retry import retry_async

logger = StructuredLogger("orchestrator")

class ScrapeOrchestrator:
    def __init__(self):
        self.static_renderer = StaticRenderer()
        self.browser_renderer = BrowserRenderer()
        self.extractor = ContentExtractor()
        self.postprocessor = PostProcessor()
        self.robots = RobotsChecker(user_agent="MCPBot")

    async def scrape(self, url: str, request_id: str) -> dict:
        start = time.time()
        logger.info("scrape_start", request_id=request_id, url=url)

        if not self.robots.allowed(url):
            logger.error("robots_blocked", request_id=request_id, url=url)
            return {
                "success": False,
                "diagnostics": {
                    "request_id": request_id,
                    "failure_reason": "blocked_by_robots"
                }
            }

        try:
            probe = await retry_async(lambda: self._probe(url, request_id))
            mode = self._classify(probe)

            diagnostics = {
                "request_id": request_id,
                "probe_mode": mode,
                "fallback_used": False,
                "failure_reason": None,
            }

            if mode == "static":
                html = await retry_async(lambda: self.static_renderer.render(url, request_id))
                extracted = self.extractor.extract(html, request_id)

                if not extracted["success"]:
                    diagnostics["fallback_used"] = True
                    html = await retry_async(lambda: self.browser_renderer.render(url, request_id))
                    extracted = self.extractor.extract(html, request_id)

            elif mode == "dynamic":
                html = await retry_async(lambda: self.browser_renderer.render(url, request_id))
                extracted = self.extractor.extract(html, request_id)

                if not extracted["success"]:
                    diagnostics["fallback_used"] = True
                    html = await retry_async(lambda: self.browser_renderer.render(url, request_id, slow=True))
                    extracted = self.extractor.extract(html, request_id)

            else:
                diagnostics["failure_reason"] = "blocked"
                return {"success": False, "diagnostics": diagnostics}

            final = self.postprocessor.process(extracted, request_id)
            final["diagnostics"].update(diagnostics)

            elapsed = round(time.time() - start, 2)
            logger.info("scrape_complete", request_id=request_id, duration_sec=elapsed)

            return final

        except Exception as e:
            error_msg = str(e)
            failure_reason = "retry_exhausted"
            screenshot_path = None

            if "captcha_detected" in error_msg:
                failure_reason = "captcha_detected"
                screenshot_path = error_msg.split("captcha_detected:")[-1]

            elif "rendered_html_too_small" in error_msg:
                failure_reason = "render_failed_empty"
                screenshot_path = error_msg.split("rendered_html_too_small:")[-1]

            logger.error(
                "scrape_failed",
                request_id=request_id,
                error=error_msg,
                failure_reason=failure_reason,
                screenshot=screenshot_path
            )

            return {
                "success": False,
                "diagnostics": {
                    "request_id": request_id,
                    "failure_reason": failure_reason,
                    "screenshot": screenshot_path,
                    "error": error_msg
                }
            }

    async def _probe(self, url: str, request_id: str):
        logger.info("probe_start", request_id=request_id, url=url)
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(url)
            html = r.text
            probe = {
                "status": r.status_code,
                "html_len": len(html),
                "text_len": len("".join(html.split())),
                "script_count": html.count("<script"),
                "has_root": "id=\"root\"" in html,
            }
            logger.info("probe_complete", request_id=request_id, **probe)
            return probe

    def _classify(self, probe: dict) -> str:
        if probe["status"] in (403, 429):
            return "blocked"
        if probe["text_len"] / max(probe["html_len"], 1) > 0.2:
            return "static"
        if probe["script_count"] > 5 or probe["has_root"]:
            return "dynamic"
        return "static"