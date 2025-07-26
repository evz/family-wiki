"""
Tests for app configuration
"""

import os

import pytest

from web_app import Config


class TestConfig:
    """Test configuration class"""

    def test_config_requires_all_env_vars(self):
        """Test that config fails when required env vars are missing"""
        # Clear all environment variables
        env_vars = ['SECRET_KEY', 'DATABASE_URL', 'CELERY_BROKER_URL',
                   'CELERY_RESULT_BACKEND', 'OLLAMA_HOST', 'OLLAMA_PORT', 'OLLAMA_MODEL']

        original_values = {}
        for var in env_vars:
            original_values[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]

        try:
            # Should fail with missing SECRET_KEY
            with pytest.raises(RuntimeError, match="Required environment variable SECRET_KEY is not set"):
                Config()
        finally:
            # Restore original values
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value

    def test_config_with_all_required_vars(self):
        """Test config works when all env vars are provided"""
        env_vars = {
            'SECRET_KEY': 'test-secret',
            'DATABASE_URL': 'postgresql://test:test@localhost:5432/test',
            'CELERY_BROKER_URL': 'redis://localhost:6379/0',
            'CELERY_RESULT_BACKEND': 'redis://localhost:6379/1',
            'OLLAMA_HOST': 'localhost',
            'OLLAMA_PORT': '11434',
            'OLLAMA_MODEL': 'test-model'
        }

        # Store original values
        original_values = {}
        for var in env_vars:
            original_values[var] = os.environ.get(var)

        try:
            # Set test values
            for var, value in env_vars.items():
                os.environ[var] = value

            # Config should work
            config = Config()

            # Verify values are set correctly
            assert config.secret_key == 'test-secret'
            assert config.sqlalchemy_database_uri == 'postgresql://test:test@localhost:5432/test'
            assert config.celery_broker_url == 'redis://localhost:6379/0'
            assert config.celery_result_backend == 'redis://localhost:6379/1'
            assert config.ollama_host == 'localhost'
            assert config.ollama_port == 11434
            assert config.ollama_model == 'test-model'

        finally:
            # Restore original values
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]

    def test_ollama_base_url_property(self):
        """Test ollama_base_url property constructs URL correctly"""
        env_vars = {
            'SECRET_KEY': 'test-secret',
            'DATABASE_URL': 'postgresql://test:test@localhost:5432/test',
            'CELERY_BROKER_URL': 'redis://localhost:6379/0',
            'CELERY_RESULT_BACKEND': 'redis://localhost:6379/1',
            'OLLAMA_HOST': '192.168.1.100',
            'OLLAMA_PORT': '8080',
            'OLLAMA_MODEL': 'test-model'
        }

        # Store original values
        original_values = {}
        for var in env_vars:
            original_values[var] = os.environ.get(var)

        try:
            # Set test values
            for var, value in env_vars.items():
                os.environ[var] = value

            config = Config()
            assert config.ollama_base_url == 'http://192.168.1.100:8080'

        finally:
            # Restore original values
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]

    def test_specific_missing_env_vars(self):
        """Test specific error messages for each missing env var"""
        required_vars = ['SECRET_KEY', 'DATABASE_URL', 'CELERY_BROKER_URL',
                        'CELERY_RESULT_BACKEND', 'OLLAMA_HOST', 'OLLAMA_PORT', 'OLLAMA_MODEL']

        for missing_var in required_vars:
            # Store original values
            original_values = {}
            for var in required_vars:
                original_values[var] = os.environ.get(var)

            try:
                # Set all except the one we're testing
                for var in required_vars:
                    if var == missing_var:
                        if var in os.environ:
                            del os.environ[var]
                    else:
                        # OLLAMA_PORT needs to be a valid integer
                        os.environ[var] = '11434' if var == 'OLLAMA_PORT' else 'test-value'

                # Should fail with specific error message
                with pytest.raises(RuntimeError, match=f"Required environment variable {missing_var} is not set"):
                    Config()

            finally:
                # Restore original values
                for var, value in original_values.items():
                    if value is not None:
                        os.environ[var] = value
                    elif var in os.environ:
                        del os.environ[var]
