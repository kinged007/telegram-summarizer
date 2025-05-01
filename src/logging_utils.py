"""
Logging utilities module for Telegram Summarizer.
Contains functions for setting up and configuring logging.
"""

import os
import sys
from datetime import datetime
from loguru import logger

def setup_logging(debug_mode=False):
    """
    Set up logging configuration based on debug mode.
    
    Args:
        debug_mode (bool): Whether to enable debug mode
        
    Returns:
        str: Path to the log file (if created)
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    # Generate log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(logs_dir, f"telegram_summarizer_{timestamp}.log")

    # Remove default logger
    logger.remove()
    if debug_mode:
        # Add console handler with DEBUG level when debug mode is enabled
        # Don't log to file in debug mode
        logger.add(sys.stderr, level="DEBUG")
        logger.debug("Logging initialized in debug mode (console only).")
    else:
        # Only log to file when not in debug mode
        logger.add(log_file, level="DEBUG", rotation="10 MB", retention="1 week")
        logger.debug("Logging initialized.")

    return log_file
