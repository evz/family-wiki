"""
API response formatting utilities for consistent API responses across blueprints
"""

from typing import Any

from flask import jsonify


class APIResponseFormatter:
    """Utility class for formatting consistent API responses"""

    @staticmethod
    def success(data: Any = None, message: str = "", status_code: int = 200) -> tuple:
        """Format a successful API response"""
        response = {
            'success': True,
            'message': message
        }

        if data is not None:
            if isinstance(data, dict):
                response.update(data)
            else:
                response['data'] = data

        return jsonify(response), status_code

    @staticmethod
    def error(error_message: str, status_code: int = 400, details: dict | None = None) -> tuple:
        """Format an error API response"""
        response = {
            'success': False,
            'error': error_message
        }

        if details:
            response['details'] = details

        return jsonify(response), status_code

    @staticmethod
    def service_result(result: dict, default_error_message: str = "Operation failed") -> tuple:
        """Convert service layer result to API response"""
        if result.get('success', False):
            return APIResponseFormatter.success(
                data=result.get('results', {}),
                message=result.get('message', '')
            )
        else:
            return APIResponseFormatter.error(
                result.get('error', default_error_message),
                status_code=500
            )

    @staticmethod
    def tool_execution_result(result: dict):
        """Format tool execution results to match CLI output format"""
        if result.get('success', False):
            return jsonify({
                'success': True,
                'stdout': result.get('message', ''),
                'stderr': '',
                'return_code': 0,
                'results': result.get('results', {})
            })
        else:
            return jsonify({
                'success': False,
                'stdout': '',
                'stderr': result.get('error', 'Unknown error'),
                'return_code': 1
            })

    @staticmethod
    def pagination_response(items: list, total: int, page: int, per_page: int,
                          item_formatter: callable = None) -> tuple:
        """Format paginated response"""
        formatted_items = items
        if item_formatter:
            formatted_items = [item_formatter(item) for item in items]

        return APIResponseFormatter.success({
            'items': formatted_items,
            'pagination': {
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            }
        })

    @staticmethod
    def validate_json_request(request_data: dict, required_fields: list) -> tuple | None:
        """Validate JSON request data and return error response if invalid"""
        if not request_data:
            return APIResponseFormatter.error('No data provided')

        missing_fields = [field for field in required_fields if not request_data.get(field)]
        if missing_fields:
            return APIResponseFormatter.error(
                f"Missing required fields: {', '.join(missing_fields)}"
            )

        return None
