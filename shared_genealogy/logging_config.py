"""
Common logging configuration for the family wiki project
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logger(name: str, level: str = "INFO", log_file: str = None) -> logging.Logger:
    """
    Setup a logger with consistent formatting across the project
    
    Args:
        name: Logger name (typically __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers if logger already configured
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_project_logger(module_name: str, verbose: bool = False) -> logging.Logger:
    """
    Get a logger configured for the family wiki project
    
    Args:
        module_name: Name of the module (typically __name__)
        verbose: Enable debug level logging
        
    Returns:
        Configured logger
    """
    level = "DEBUG" if verbose else "INFO"
    
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Log file with timestamp
    log_file = logs_dir / f"family_wiki_{datetime.now().strftime('%Y%m%d')}.log"
    
    return setup_logger(module_name, level, str(log_file))

def setup_module_logger(module_name: str, verbose: bool = False) -> logging.Logger:
    """
    Convenience function for modules to get a configured logger
    
    Usage:
        from shared_genealogy.logging_config import setup_module_logger
        logger = setup_module_logger(__name__)
    """
    return get_project_logger(module_name, verbose)