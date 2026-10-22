from utils.structured_logger import StructuredLogger

logger = StructuredLogger("postprocessor")

class PostProcessor:
    def process(self, extracted: dict, request_id: str) -> dict:
        logger.info("postprocess_start", request_id=request_id)

        text = self._normalize(extracted["text"])
        blocks = self._structure(text)

        words = text.split()
        paras = text.count("\n")

        quality = {
            "word_count": len(words),
            "paragraph_count": paras,
            "quality_score": round(min(len(words) / 1500, 1.0), 2),
        }

        logger.info("postprocess_done", request_id=request_id, **quality)

        return {
            "success": True,
            "content": {
                "text": text,
                "blocks": blocks,
            },
            "quality": quality,
            "diagnostics": {
                "extractor": extracted["strategy"],
                "failure_reason": None,
            },
        }

    def _normalize(self, text: str) -> str:
        return " ".join(text.split())

    def _structure(self, text: str):
        parts = [p.strip() for p in text.split("\n") if p.strip()]
        return [{"type": "paragraph", "text": p} for p in parts[:100]]