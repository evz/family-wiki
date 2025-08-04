"""
System configuration and status service for checking external dependencies and managing embedding models
"""
import os

import requests
from flask import current_app

from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)


# Curated list of recommended embedding models optimized for multilingual use cases
# Prioritized for English questions about Dutch text - using exact Ollama paths
RECOMMENDED_EMBEDDING_MODELS = {
        'zylonai/multilingual-e5-large:latest': {
        'name': 'Multilingual E5 Large',
        'description': 'State-of-the-art multilingual embedding model from Microsoft. Excellent for cross-language retrieval (English questions, Dutch content).',
        'use_cases': 'Cross-language search, multilingual documents, Dutch-English genealogy',
        'size': 'Large (~1.2GB)',
        'speed': 'Slower',
        'languages': '100+ languages including Dutch and English',
        'cross_language': True,
        'recommended_for_dutch': True,
        'display_name': 'multilingual-e5-large'
    },
    'qllama/multilingual-e5-base': {
        'name': 'Multilingual E5 Base (Recent)',
        'description': 'Balanced multilingual model with good performance and reasonable speed. Great for Dutch-English cross-language queries. Recently updated quantized version.',
        'use_cases': 'Cross-language search, multilingual genealogy documents',
        'size': 'Medium (~440MB)',
        'speed': 'Medium',
        'languages': '100+ languages including Dutch and English',
        'cross_language': True,
        'recommended_for_dutch': True,
        'display_name': 'multilingual-e5-base'
    },
    'dengcao/bge-m3': {
        'name': 'BGE M3 Multilingual (Recent)',
        'description': 'High-performance multilingual model from Beijing Academy of AI. Most recently updated version with excellent semantic understanding across languages.',
        'use_cases': 'Multilingual document search, cross-language retrieval',
        'size': 'Large (~2.2GB)',
        'speed': 'Slower',
        'languages': '100+ languages including Dutch and English',
        'cross_language': True,
        'recommended_for_dutch': True,
        'display_name': 'bge-m3'
    },
    'nomic-embed-text': {
        'name': 'Nomic Embed Text',
        'description': 'General-purpose embedding model with some multilingual capabilities. Decent fallback option.',
        'use_cases': 'General text, mixed language documents',
        'size': 'Medium (~274MB)',
        'speed': 'Fast',
        'languages': 'Primarily English, limited multilingual',
        'cross_language': False,
        'recommended_for_dutch': False,
        'display_name': 'nomic-embed-text'
    },
    'all-minilm': {
        'name': 'All MiniLM',
        'description': 'Fast multilingual sentence transformer. Good speed but lower quality than E5/BGE models.',
        'use_cases': 'Fast multilingual search, large document collections',
        'size': 'Small (~80MB)',
        'speed': 'Very Fast',
        'languages': '50+ languages including Dutch and English',
        'cross_language': True,
        'recommended_for_dutch': False,
        'display_name': 'all-minilm'
    }
}

# Default model prioritizing multilingual capabilities - using the large E5 model
DEFAULT_EMBEDDING_MODEL = 'zylonai/multilingual-e5-large:latest'

class SystemService:
    """Service for checking system status, external dependencies, and managing embedding models"""

    def __init__(self):
        self.logger = get_project_logger(__name__)
        self.ollama_host = os.environ.get('OLLAMA_HOST', 'localhost')
        self.ollama_port = os.environ.get('OLLAMA_PORT', '11434')

    def _get_ollama_base_url(self) -> str:
        """Get Ollama base URL using current Flask config or fallback to environment"""
        try:
            # Try to use Flask config if available
            ollama_host = current_app.config.get('OLLAMA_HOST', self.ollama_host)
            ollama_port = current_app.config.get('OLLAMA_PORT', int(self.ollama_port))
            return f"http://{ollama_host}:{ollama_port}"
        except RuntimeError:
            # Fallback to environment variables if no Flask context
            return f"http://{self.ollama_host}:{self.ollama_port}"

    def check_ollama_status(self) -> dict:
        """Check if Ollama server is running and return detailed status"""
        try:
            ollama_base_url = self._get_ollama_base_url()
            response = requests.get(f"{ollama_base_url}/api/tags", timeout=5)
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

    def get_available_embedding_models(self) -> list[dict[str, str]]:
        """
        Get list of available embedding models from Ollama server
        Falls back to recommended models if Ollama is unavailable

        Returns:
            List of model dictionaries with name and info
        """
        try:
            ollama_base_url = self._get_ollama_base_url()
            response = requests.get(f"{ollama_base_url}/api/tags", timeout=5)

            if response.status_code == 200:
                ollama_models = response.json().get('models', [])
                available_embedding_models = []

                # Filter for embedding models that are actually available
                for model_id, model_info in RECOMMENDED_EMBEDDING_MODELS.items():
                    # Check if this embedding model is available in Ollama
                    model_available = any(
                        model_id in ollama_model['name']
                        for ollama_model in ollama_models
                    )

                    available_embedding_models.append({
                        'id': model_id,
                        'name': model_info['name'],
                        'description': model_info['description'],
                        'use_cases': model_info['use_cases'],
                        'size': model_info['size'],
                        'speed': model_info['speed'],
                        'languages': model_info['languages'],
                        'cross_language': model_info['cross_language'],
                        'recommended_for_dutch': model_info['recommended_for_dutch'],
                        'display_name': model_info['display_name'],
                        'available': model_available
                    })

                return available_embedding_models

        except Exception as e:
            logger.warning(f"Could not connect to Ollama to check available models: {e}")

        # Fallback to recommended models - all marked as unavailable since Ollama is not accessible
        return [
            {
                'id': model_id,
                'name': model_info['name'],
                'description': model_info['description'],
                'use_cases': model_info['use_cases'],
                'size': model_info['size'],
                'speed': model_info['speed'],
                'languages': model_info['languages'],
                'cross_language': model_info['cross_language'],
                'recommended_for_dutch': model_info['recommended_for_dutch'],
                'display_name': model_info['display_name'],
                'available': False  # All unavailable since Ollama is not accessible
            }
            for model_id, model_info in RECOMMENDED_EMBEDDING_MODELS.items()
        ]

    def validate_embedding_model(self, model_id: str) -> bool:
        """
        Validate that an embedding model ID is supported

        Args:
            model_id: The embedding model identifier

        Returns:
            True if model is valid/supported
        """
        return model_id in RECOMMENDED_EMBEDDING_MODELS

    def get_model_info(self, model_id: str) -> dict[str, str]:
        """
        Get information about a specific embedding model

        Args:
            model_id: The embedding model identifier

        Returns:
            Dictionary with model information
        """
        return RECOMMENDED_EMBEDDING_MODELS.get(model_id, {
            'name': model_id,
            'description': 'Custom embedding model',
            'use_cases': 'Unknown',
            'size': 'Unknown',
            'speed': 'Unknown'
        })

