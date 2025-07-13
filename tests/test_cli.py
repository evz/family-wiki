"""
Tests for the CLI interface
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from family_wiki_cli import cli

def test_cli_help():
    """Test CLI help output"""
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    
    assert result.exit_code == 0
    assert "Family Wiki - Genealogy Processing Tools" in result.output
    assert "ocr" in result.output
    assert "extract" in result.output
    assert "gedcom" in result.output

def test_cli_verbose_flag():
    """Test that verbose flag is passed correctly"""
    runner = CliRunner()
    
    with patch('family_wiki_cli.get_project_logger') as mock_logger:
        mock_logger.return_value = MagicMock()
        result = runner.invoke(cli, ['--verbose', 'gedcom'])
        
        # Should have been called with verbose=True
        mock_logger.assert_called_with('family_wiki_cli', True)

@pytest.mark.skip(reason="OCR command requires actual PDF files and OCR setup")
def test_ocr_command():
    """Test OCR command execution"""
    runner = CliRunner()
    
    # Skip this test as it requires actual PDF processing setup
    # This would be better as an integration test
    result = runner.invoke(cli, ['ocr'])
    
    # The command should handle the error gracefully
    assert result.exit_code in [0, 1]  # Either success or handled error

def test_gedcom_command_success():
    """Test successful GEDCOM command"""
    runner = CliRunner()
    
    with patch('gedcom_generator.main') as mock_gedcom:
        mock_gedcom.return_value = None
        result = runner.invoke(cli, ['gedcom'])
        
        assert result.exit_code == 0
        mock_gedcom.assert_called_once()

def test_gedcom_command_failure():
    """Test GEDCOM command with exception"""
    runner = CliRunner()
    
    with patch('gedcom_generator.main') as mock_gedcom:
        mock_gedcom.side_effect = Exception("Test error")
        result = runner.invoke(cli, ['gedcom'])
        
        assert result.exit_code == 1
        assert "Test error" in result.output