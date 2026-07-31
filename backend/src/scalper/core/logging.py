import json
import logging
from datetime import UTC, datetime
from typing import Any

_RESERVED = {"timestamp", "level", "logger", "event", "message"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
            "message": record.getMessage(),
        }
        context = getattr(record, "context", {})
        if isinstance(context, dict):
            payload.update({key: value for key, value in context.items() if key not in _RESERVED})
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def log_event(event: str, message: str | None = None, **context: Any) -> None:
    logging.getLogger("scalper").info(
        message or event,
        extra={"event": event, "context": context},
    )
