"""
Utility functions for service operations
"""

from collections.abc import Callable

from web_app.shared.logging_config import get_project_logger


def execute_with_progress(operation_name: str, operation_func: Callable, progress_callback: Callable = None, **kwargs) -> dict:
    """
    Execute an operation with standardized progress tracking and error handling

    Args:
        operation_name: Human-readable name for the operation
        operation_func: Function to execute
        progress_callback: Optional progress callback function
        **kwargs: Arguments to pass to operation_func

    Returns:
        dict: Standardized result with success/error status
    """
    logger = get_project_logger(operation_func.__module__)

    try:
        logger.info(f"Starting {operation_name}")

        if progress_callback:
            progress_callback({"status": "starting", "message": f"Initializing {operation_name}"})

        # Execute the operation
        result = operation_func(**kwargs)

        if progress_callback:
            progress_callback({"status": "completed", "results": result})

        logger.info(f"{operation_name} completed successfully")

        return {
            "success": True,
            "message": f"{operation_name} completed",
            "results": result
        }

    except Exception as e:
        error_msg = f"{operation_name} failed: {str(e)}"
        logger.error(error_msg)

        if progress_callback:
            progress_callback({"status": "failed", "error": error_msg})

        return {
            "success": False,
            "error": error_msg
        }
