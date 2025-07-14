"""
Tests for the logging configuration module
"""

import logging

from web_app.shared.logging_config import get_project_logger, setup_logger


def test_setup_logger_basic():
    """Test basic logger setup"""
    logger = setup_logger("test_logger")

    assert logger.name == "test_logger"
    assert logger.level == logging.INFO
    assert len(logger.handlers) >= 1  # At least console handler

def test_setup_logger_with_debug():
    """Test logger setup with debug level"""
    logger = setup_logger("test_debug", level="DEBUG")

    assert logger.level == logging.DEBUG

def test_setup_logger_with_file(temp_dir):
    """Test logger setup with file output"""
    log_file = temp_dir / "test.log"
    logger = setup_logger("test_file", log_file=str(log_file))

    # Log a test message
    logger.info("Test message")

    # Check file was created and contains message
    assert log_file.exists()
    content = log_file.read_text()
    assert "Test message" in content

def test_get_project_logger():
    """Test project logger creation"""
    logger = get_project_logger("test_module")

    assert logger.name == "test_module"
    assert logger.level == logging.INFO

def test_get_project_logger_verbose():
    """Test project logger with verbose mode"""
    # Clear any existing loggers to avoid conflicts
    logger_name = "test_module_verbose"
    if logger_name in logging.Logger.manager.loggerDict:
        del logging.Logger.manager.loggerDict[logger_name]

    logger = get_project_logger(logger_name, verbose=True)

    assert logger.level == logging.DEBUG

def test_duplicate_logger_handlers():
    """Test that duplicate handlers aren't added"""
    logger1 = setup_logger("duplicate_test")
    initial_handlers = len(logger1.handlers)

    logger2 = setup_logger("duplicate_test")

    # Should be the same logger instance
    assert logger1 is logger2
    assert len(logger2.handlers) == initial_handlers
