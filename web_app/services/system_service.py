"""
System status service for checking external dependencies
"""


import requests

from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

class SystemService:
    """Service for checking system status and external dependencies"""

    def __init__(self):
        self.logger = get_project_logger(__name__)

    def check_ollama_status(self) -> dict:
        """Check if Ollama server is running and return detailed status"""
        try:
            response = requests.get("http://192.168.1.234:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model.get('name', 'Unknown') for model in models]

                return {
                    "available": True,
                    "status": "running",
                    "models_count": len(models),
                    "models": model_names,
                    "message": f"Ollama is running with {len(models)} models available"
                }
        except requests.exceptions.ConnectionError:
            return {
                "available": False,
                "status": "not_running",
                "models_count": 0,
                "models": [],
                "message": "Ollama server is not running. Please start Ollama to use AI extraction.",
                "help": "Run 'ollama serve' in terminal or start Ollama application"
            }
        except requests.exceptions.Timeout:
            return {
                "available": False,
                "status": "timeout",
                "models_count": 0,
                "models": [],
                "message": "Ollama server is not responding (timeout)",
                "help": "Check if Ollama is running properly"
            }
        except Exception as e:
            return {
                "available": False,
                "status": "error",
                "models_count": 0,
                "models": [],
                "message": f"Error checking Ollama: {str(e)}",
                "help": "Check Ollama installation and configuration"
            }

    def check_system_status(self) -> dict:
        """Check overall system status including all dependencies"""
        ollama_status = self.check_ollama_status()

        # Check if text files exist
        from pathlib import Path
        text_file = Path("web_app/pdf_processing/extracted_text/consolidated_text.txt")
        text_available = text_file.exists()

        # Overall system health
        all_ready = ollama_status["available"] and text_available

        return {
            "overall_status": "ready" if all_ready else "needs_attention",
            "ollama": ollama_status,
            "text_data": {
                "available": text_available,
                "path": str(text_file),
                "message": "OCR text data available" if text_available else "No OCR text data found. Run OCR processing first."
            },
            "extraction_ready": ollama_status["available"] and text_available
        }

# Global service instance
system_service = SystemService()
