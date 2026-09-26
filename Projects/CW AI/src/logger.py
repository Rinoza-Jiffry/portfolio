
from __future__ import annotations
import logging
import logging.handlers
import sys
from pathlib import Path
from config import LOGGING, PATHS

_COLOURS = {
    "DEBUG":    "\033[36m",
    "INFO":     "\033[32m",
    "WARNING":  "\033[33m",
    "ERROR":    "\033[31m",
    "CRITICAL": "\033[35m",
    "RESET":    "\033[0m",
}

class ColourFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        colour    = _COLOURS.get(record.levelname, "")
        reset     = _COLOURS["RESET"]
        record    = logging.makeLogRecord(record.__dict__)
        record.levelname = f"{colour}{record.levelname:<8}{reset}"
        return super().format(record)

_configured = False

def _setup_root_logger() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(getattr(logging, LOGGING["level"], logging.INFO))

    plain_fmt   = logging.Formatter(LOGGING["format"], datefmt=LOGGING["date_format"])
    colour_fmt  = ColourFormatter(LOGGING["format"], datefmt=LOGGING["date_format"])

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(colour_fmt if sys.stdout.isatty() else plain_fmt)
    root.addHandler(console)

    log_path: Path = LOGGING["log_file"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes  = LOGGING["max_bytes"],
        backupCount = LOGGING["backup_count"],
        encoding  = "utf-8",
    )
    file_handler.setFormatter(plain_fmt)
    root.addHandler(file_handler)

def get_logger(name: str) -> logging.Logger:
    _setup_root_logger()
    return logging.getLogger(name)

if __name__ == "__main__":
    log = get_logger("logger.test")
    log.debug("Debug message — fine-grained tracing")
    log.info("Info message — normal operation")
    log.warning("Warning message — something unexpected but recoverable")
    log.error("Error message — an operation failed")
    log.critical("Critical message — system integrity at risk")
    print(f"\nLog file: {LOGGING['log_file']}")
