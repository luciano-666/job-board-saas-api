import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog for structured JSON output.

    Call once at application startup (lifespan or module level).
    All loggers — stdlib and structlog — emit JSON to stdout.
    """
    shared_processors: list[structlog.types.Processor] = [
        # Inject log level and logger name from stdlib records
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        # Timestamp in ISO-8601
        structlog.processors.TimeStamper(fmt="iso"),
        # Render exceptions inline as a string
        structlog.processors.format_exc_info,
        # Drop _record and _from_structlog keys added by stdlib integration
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            # Pass through to stdlib sink configured below
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        # Final renderer — JSON to stdout
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)

    # Quiet noisy libs
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
