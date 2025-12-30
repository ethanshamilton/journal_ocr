import json
import logging
import sys
from datetime import datetime
from pathlib import Path

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }

        if hasattr(record, "metrics"):
            log_data["metrics"] = record.metrics

        return json.dumps(log_data)

class ConsoleFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',    # cyan
        'INFO': '\033[32m',     # green
        'WARNING': '\033[33m',  # yellow
        'ERROR': '\033[31m',    # red
        'CRITICAL': '\033[35m', # magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = self.COLORS.get(record.levelname, '')
        msg = record.getMessage()

        if hasattr(record, "metrics"):
            metrics_str = " | ".join(f"{k}={v}" for k, v in record.metrics.items())
            return f"{timestamp} {color}[{record.levelname}]{self.RESET} {msg} | {metrics_str}"

        return f"{timestamp} {color}[{record.levelname}]{self.RESET} {msg}"

def setup_logging(log_dir: Path = Path("./logs"), debug: bool = False):

    logger = logging.getLogger("journal_app")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ConsoleFormatter())
    logger.addHandler(console_handler)

    if log_dir.exists():
        file_handler = logging.FileHandler(log_dir / "journal_app.jsonl")
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    return logger
