from lxml import html
from utils.structured_logger import StructuredLogger

logger = StructuredLogger("extractor")

class ContentExtractor:
    def extract(self, html_text: str, request_id: str) -> dict:
        logger.info("extract_start", request_id=request_id)

        tree = html.fromstring(html_text)
        candidates = tree.xpath("//article | //main | //section | //div")

        best = None
        best_score = 0

        for node in candidates:
            text = node.text_content().strip()
            if len(text) < 200:
                continue

            links = len(node.xpath(".//a"))
            forms = len(node.xpath(".//form"))
            paras = len(node.xpath(".//p"))

            score = len(text) + paras * 50 - links * 100 - forms * 200

            if score > best_score:
                best_score = score
                best = node

        if best is None:
            logger.error("extract_fail", request_id=request_id, reason="no_content_block")
            return {"success": False, "reason": "no_content_block"}

        cleaned = self._clean(best)
        text = cleaned.text_content().strip()

        logger.info("extract_success", request_id=request_id, chars=len(text))
        return {
            "success": True,
            "strategy": "density_scoring",
            "html": html.tostring(cleaned, encoding="unicode"),
            "text": text,
        }

    def _clean(self, node):
        for bad in node.xpath(".//script|.//style|.//nav|.//footer|.//aside|.//form"):
            bad.getparent().remove(bad)
        return node