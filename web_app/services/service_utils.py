"""
Utility functions for service layer error handling
"""

from functools import wraps
from flask import flash, redirect, url_for
from web_app.services.exceptions import ServiceError, ValidationError, NotFoundError, ConflictError

def handle_service_errors(redirect_endpoint='main.index', success_message=None):
    """
    Decorator to handle service errors and convert them to flash messages
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                if success_message:
                    flash(success_message, 'success')
                return result
            except ValidationError as e:
                flash(f'Validation error: {str(e)}', 'error')
                return redirect(url_for(redirect_endpoint))
            except NotFoundError as e:
                flash(f'Not found: {str(e)}', 'error')
                return redirect(url_for(redirect_endpoint))
            except ConflictError as e:
                flash(f'Conflict: {str(e)}', 'error')
                return redirect(url_for(redirect_endpoint))
            except ServiceError as e:
                flash(f'Error: {str(e)}', 'error')
                return redirect(url_for(redirect_endpoint))
            except Exception as e:
                flash(f'Unexpected error: {str(e)}', 'error')
                return redirect(url_for(redirect_endpoint))
        return wrapper
    return decorator