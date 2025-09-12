"""
Logging Configuration for Chess RAG System.

Provides centralized logging setup with appropriate formatters,
handlers, and log levels for different system components.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(log_level: str = "INFO", log_file: str = None, console_output: bool = True):
    """
    Setup centralized logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        console_output: Whether to output to console
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all levels

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)

        if numeric_level <= logging.DEBUG:
            console_handler.setFormatter(detailed_formatter)
        else:
            console_handler.setFormatter(console_formatter)

        root_logger.addHandler(console_handler)

    # File handler
    if log_file is None:
        log_file = f"chess_rag_system_{datetime.now().strftime('%Y%m%d')}.log"

    try:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always detailed in file
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not create log file {log_file}: {e}")

    # Set levels for specific loggers
    logging.getLogger('chess_rag_system').setLevel(numeric_level)

    # Reduce noise from external libraries
    logging.getLogger('transformers').setLevel(logging.WARNING)
    logging.getLogger('torch').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    return root_logger


def get_module_logger(module_name: str) -> logging.Logger:
    """Get a logger for a specific module"""
    return logging.getLogger(f'chess_rag_system.{module_name}')


class ProgressLogger:
    """Logger that integrates with progress tracking"""

    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
        self.progress_callback = None

    def set_progress_callback(self, callback):
        """Set callback for progress updates"""
        self.progress_callback = callback

    def info_with_progress(self, message: str, progress_data: dict = None):
        """Log info message and update progress if callback set"""
        self.logger.info(message)
        if self.progress_callback and progress_data:
            self.progress_callback(progress_data)

    def debug_analysis_step(self, step_name: str, result: dict):
        """Log detailed analysis step for debugging"""
        self.logger.debug(f"Analysis step '{step_name}' completed: {result}")


def configure_evs_debugging():
    """Configure enhanced logging for EVS integration debugging"""
    # Create specific logger for EVS debugging
    evs_logger = logging.getLogger('chess_rag_system.evs_integration')
    evs_logger.setLevel(logging.DEBUG)

    # Create EVS-specific log file
    evs_handler = logging.FileHandler('evs_integration_debug.log')
    evs_handler.setLevel(logging.DEBUG)

    evs_formatter = logging.Formatter(
        '%(asctime)s - EVS_DEBUG - %(message)s'
    )
    evs_handler.setFormatter(evs_formatter)
    evs_logger.addHandler(evs_handler)

    return evs_logger