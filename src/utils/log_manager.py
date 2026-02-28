import logging
import os
import sys

LOG_LEVEL = logging.INFO
LOG_FORMAT = os.environ.get("LOG_FORMAT", "text").lower()


def setup_logger(name: str) -> logging.Logger:
    """Configures and returns a dedicated, standardized logger instance."""

    log = logging.getLogger(name)

    if not log.handlers:
        log.setLevel(LOG_LEVEL)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)

        log.addHandler(handler)

    return log


class CustomLogger:
    """
    A wrapper class around the standard Python logger instance
    """

    def __init__(self, logger_instance: logging.Logger):
        """Initializes the wrapper with the configured logger instance."""
        self._logger = logger_instance

    def _log_with_extra(
        self,
        level: int,
        message: str,
    ) -> None:
        """
        Generic method to construct the 'extra' dictionary and call the underlying logger,
        using stacklevel to correctly identify the calling module (skipping the wrapper layer).
        """
        self._logger.log(level, message, stacklevel=3)

    def info(self, message: str) -> None:
        """Logs a message with level INFO"""
        self._log_with_extra(logging.INFO, message)

    def warning(self, message: str) -> None:
        """Logs a message with level WARNING"""
        self._log_with_extra(logging.WARNING, message)

    def error(self, message: str) -> None:
        """Logs a message with level ERROR"""
        self._log_with_extra(logging.ERROR, message)

    def debug(self, message: str) -> None:
        """Logs a message with level DEBUG"""
        self._log_with_extra(logging.DEBUG, message)

    def critical(self, message: str) -> None:
        """Logs a message with level CRITICAL"""
        self._log_with_extra(logging.CRITICAL, message)


standard_logger = setup_logger(__name__)

logger = CustomLogger(standard_logger)
