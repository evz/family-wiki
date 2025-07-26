"""
Tests for embedding model configuration and management
"""

import pytest
import requests
import requests_mock

from web_app.services.embedding_models import (
    DEFAULT_EMBEDDING_MODEL,
    RECOMMENDED_EMBEDDING_MODELS,
    get_available_embedding_models,
    get_model_info,
    validate_embedding_model,
)


class TestEmbeddingModels:
    """Test embedding model configuration and management"""

    def test_recommended_models_structure(self):
        """Test that recommended models have the correct structure"""
        for model_id, model_info in RECOMMENDED_EMBEDDING_MODELS.items():
            # Check required fields
            assert 'name' in model_info
            assert 'description' in model_info
            assert 'use_cases' in model_info
            assert 'size' in model_info
            assert 'speed' in model_info
            assert 'languages' in model_info
            assert 'cross_language' in model_info
            assert 'recommended_for_dutch' in model_info
            assert 'display_name' in model_info

            # Check field types
            assert isinstance(model_info['name'], str)
            assert isinstance(model_info['description'], str)
            assert isinstance(model_info['cross_language'], bool)
            assert isinstance(model_info['recommended_for_dutch'], bool)

    def test_default_model_exists(self):
        """Test that the default model exists in recommended models"""
        assert DEFAULT_EMBEDDING_MODEL in RECOMMENDED_EMBEDDING_MODELS

    def test_default_model_is_multilingual(self):
        """Test that the default model supports multilingual use case"""
        default_model = RECOMMENDED_EMBEDDING_MODELS[DEFAULT_EMBEDDING_MODEL]
        assert default_model['cross_language'] is True
        assert default_model['recommended_for_dutch'] is True

    def test_multilingual_models_prioritized(self):
        """Test that multilingual models are properly marked"""
        multilingual_models = [
            model_id for model_id, info in RECOMMENDED_EMBEDDING_MODELS.items()
            if info['cross_language'] and info['recommended_for_dutch']
        ]

        # Should have at least 3 good multilingual options
        assert len(multilingual_models) >= 3

        # Should include the E5 models
        assert any('multilingual-e5' in model_id for model_id in multilingual_models)

    @pytest.fixture
    def mock_ollama_response(self):
        """Mock Ollama API response with available models"""
        return {
            'models': [
                {'name': 'zylonai/multilingual-e5-large:latest'},
                {'name': 'qllama/multilingual-e5-base'},
                {'name': 'nomic-embed-text'},
                {'name': 'llama3:latest'}  # Non-embedding model
            ]
        }

    def test_get_available_models_with_ollama_success(self, app, mock_ollama_response):
        """Test getting available models when Ollama is accessible"""
        app.config['OLLAMA_HOST'] = 'localhost'
        app.config['OLLAMA_PORT'] = 11434

        with requests_mock.Mocker() as m:
            m.get('http://localhost:11434/api/tags', json=mock_ollama_response)

            models = get_available_embedding_models()

            # Should return all recommended models with availability status
            assert len(models) == len(RECOMMENDED_EMBEDDING_MODELS)

            # Check that available models are marked correctly
            available_model_ids = {model['id'] for model in models if model['available']}
            expected_available = {
                'zylonai/multilingual-e5-large:latest',
                'qllama/multilingual-e5-base',
                'nomic-embed-text'
            }
            # Check that the expected models are subset of available
            assert expected_available.issubset(available_model_ids)

    def test_get_available_models_ollama_unavailable(self, app):
        """Test getting available models when Ollama is not accessible"""
        app.config['OLLAMA_HOST'] = 'localhost'
        app.config['OLLAMA_PORT'] = 11434

        with requests_mock.Mocker() as m:
            m.get('http://localhost:11434/api/tags', status_code=500)

            models = get_available_embedding_models()

            # Should still return all recommended models
            assert len(models) == len(RECOMMENDED_EMBEDDING_MODELS)

            # All models should be marked as unavailable (the service shows all as unavailable when Ollama fails)
            available_models = [model for model in models if model['available']]
            assert len(available_models) == 0

    def test_get_available_models_connection_error(self, app):
        """Test getting available models when connection fails"""
        app.config['OLLAMA_HOST'] = 'localhost'
        app.config['OLLAMA_PORT'] = 11434

        with requests_mock.Mocker() as m:
            # Use requests.exceptions.ConnectTimeout instead
            m.get('http://localhost:11434/api/tags', exc=requests.exceptions.ConnectTimeout)

            models = get_available_embedding_models()

            # Should still return all recommended models
            assert len(models) == len(RECOMMENDED_EMBEDDING_MODELS)

            # All models should be marked as unavailable
            available_models = [model for model in models if model['available']]
            assert len(available_models) == 0

    def test_validate_embedding_model_valid(self):
        """Test validating valid embedding model IDs"""
        for model_id in RECOMMENDED_EMBEDDING_MODELS.keys():
            assert validate_embedding_model(model_id) is True

    def test_validate_embedding_model_invalid(self):
        """Test validating invalid embedding model IDs"""
        invalid_models = [
            'nonexistent-model',
            'random/fake-model:latest',
            '',
            None
        ]

        for invalid_model in invalid_models:
            assert validate_embedding_model(invalid_model) is False

    def test_get_model_info_existing(self):
        """Test getting info for existing models"""
        for model_id, expected_info in RECOMMENDED_EMBEDDING_MODELS.items():
            info = get_model_info(model_id)

            # Should return the exact model info
            assert info == expected_info

    def test_get_model_info_nonexistent(self):
        """Test getting info for nonexistent models"""
        info = get_model_info('fake-model-id')

        # Should return default structure
        assert info['name'] == 'fake-model-id'
        assert info['description'] == 'Custom embedding model'
        assert info['use_cases'] == 'Unknown'
        assert info['size'] == 'Unknown'
        assert info['speed'] == 'Unknown'

    def test_model_display_names(self):
        """Test that models have appropriate display names"""
        for model_id, model_info in RECOMMENDED_EMBEDDING_MODELS.items():
            display_name = model_info['display_name']

            # Display name should be simpler than full model ID
            assert len(display_name) <= len(model_id)

            # Should not contain slashes or colons for UI display
            assert '/' not in display_name
            assert ':' not in display_name

    def test_dutch_optimized_models_exist(self):
        """Test that we have models optimized for Dutch language tasks"""
        dutch_optimized = [
            model_id for model_id, info in RECOMMENDED_EMBEDDING_MODELS.items()
            if info['recommended_for_dutch']
        ]

        # Should have multiple Dutch-optimized options
        assert len(dutch_optimized) >= 3

        # Default should be Dutch-optimized
        assert DEFAULT_EMBEDDING_MODEL in dutch_optimized

    def test_model_paths_are_valid(self):
        """Test that model IDs follow valid Ollama naming conventions"""
        for model_id in RECOMMENDED_EMBEDDING_MODELS.keys():
            # Should not be empty
            assert model_id.strip()

            # Should follow reasonable naming patterns
            # Either simple name or namespace/name format
            if '/' in model_id:
                parts = model_id.split('/')
                assert len(parts) == 2
                assert all(part.strip() for part in parts)
