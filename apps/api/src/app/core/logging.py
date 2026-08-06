"""Configuration des logs structurés (structlog).

En local : rendu lisible en console.
En staging/production : rendu JSON (exploitable par un agrégateur de logs).
"""

import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO", *, json_logs: bool = False) -> None:
    """Configure structlog et la lib standard `logging`.

    Args:
        log_level: niveau minimal (DEBUG, INFO, WARNING, ERROR).
        json_logs: si vrai, sortie JSON ; sinon rendu console coloré.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Base de la lib standard : on écrit sur stdout au niveau demandé.
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    processors.append(
        structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Retourne un logger structuré."""
    return structlog.get_logger(name)
