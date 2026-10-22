import json
import logging
import sys
from datetime import datetime
import uuid

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stderr)
        self.logger.addHandler(handler)

    def log(self, level: str, message: str, **fields):
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **fields
        }
        self.logger.info(json.dumps(record))

    def info(self, message: str, **fields):
        self.log("INFO", message, **fields)

    def error(self, message: str, **fields):
        self.log("ERROR", message, **fields)

def new_request_id():
    return str(uuid.uuid4())