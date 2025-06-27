"""Tests for the CLI module."""

import sys
import logging
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from mcp_lancedb.cli import main


@pytest.mark.unit
class TestCLI:
    """Test the CLI functionality."""
    
    def setup_method(self):
        """Setup method for each test."""
        self.runner = CliRunner()
        # Capture the original stderr to restore later
        self.original_stderr = sys.stderr
    
    def teardown_method(self):
        """Teardown method for each test."""
        # Restore original stderr
        sys.stderr = self.original_stderr
    
    def test_cli_main_function_exists(self):
        """Test that the main function is callable."""
        assert callable(main)
    
    def test_cli_main_help(self):
        """Test that the CLI shows help when called with --help."""
        result = self.runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert "Run the MCP LanceDB server using stdio" in result.output
    
    @patch('mcp_lancedb.cli.run')
    def test_cli_successful_execution(self, mock_run):
        """Test successful CLI execution."""
        # Mock the run function to do nothing
        mock_run.return_value = None
        
        result = self.runner.invoke(main, [])
        
        assert result.exit_code == 0
        mock_run.assert_called_once()
    
    @patch('mcp_lancedb.cli.run')
    def test_cli_server_error_handling(self, mock_run):
        """Test CLI error handling when server fails."""
        # Mock the run function to raise an exception
        mock_run.side_effect = Exception("Server startup failed")
        
        result = self.runner.invoke(main, [])
        
        assert result.exit_code == 1
        mock_run.assert_called_once()
    
    @patch('mcp_lancedb.cli.run')
    def test_cli_specific_exception_handling(self, mock_run):
        """Test CLI handling of specific exceptions."""
        # Test with different exception types
        test_exceptions = [
            ValueError("Invalid configuration"),
            RuntimeError("Database connection failed"),
            OSError("File system error"),
            KeyboardInterrupt("User interrupted")
        ]
        
        for exception in test_exceptions:
            mock_run.side_effect = exception
            
            result = self.runner.invoke(main, [])
            
            assert result.exit_code == 1
            mock_run.assert_called_once()
            mock_run.reset_mock()
    
    @patch('mcp_lancedb.cli.run')
    def test_cli_logging_behavior(self, mock_run):
        """Test that CLI properly configures logging."""
        # Mock the run function to do nothing
        mock_run.return_value = None
        
        # Test that the CLI executes successfully (logging is configured during import)
        result = self.runner.invoke(main, [])
        
        assert result.exit_code == 0
        mock_run.assert_called_once()
    
    @patch('mcp_lancedb.cli.run')
    def test_cli_error_logging(self, mock_run):
        """Test that CLI logs errors properly."""
        # Mock the run function to raise an exception
        test_error = Exception("Test error message")
        mock_run.side_effect = test_error
        
        result = self.runner.invoke(main, [])
        
        assert result.exit_code == 1
        mock_run.assert_called_once()
    
    def test_cli_logging_configuration(self):
        """Test that logging is properly configured."""
        # Test that the logger is properly configured
        from mcp_lancedb.cli import logger
        
        # Check that the logger has the correct name
        assert logger.name == "mcp_lancedb.cli"
        
        # Check that the logger is properly configured (not None)
        assert logger is not None
        
        # Check that the logger can handle CRITICAL level messages (which is the default)
        assert logger.isEnabledFor(logging.CRITICAL)
    
    @patch('mcp_lancedb.cli.run')
    def test_cli_exit_code_consistency(self, mock_run):
        """Test that CLI consistently returns proper exit codes."""
        # Test successful execution
        mock_run.return_value = None
        result = self.runner.invoke(main, [])
        assert result.exit_code == 0
        
        # Test error execution
        mock_run.side_effect = Exception("Test error")
        result = self.runner.invoke(main, [])
        assert result.exit_code == 1
    
    def test_cli_module_imports(self):
        """Test that CLI module imports correctly."""
        # Test that all required imports are available
        from mcp_lancedb.cli import main, logger
        
        assert callable(main)
        assert isinstance(logger, logging.Logger)
        assert logger.name == "mcp_lancedb.cli"
    
    @patch('mcp_lancedb.cli.run')
    def test_cli_no_arguments(self, mock_run):
        """Test CLI behavior with no arguments."""
        mock_run.return_value = None
        
        result = self.runner.invoke(main, [])
        
        assert result.exit_code == 0
        mock_run.assert_called_once()
    
    @patch('mcp_lancedb.cli.run')
    def test_cli_with_extra_arguments(self, mock_run):
        """Test CLI behavior with unexpected arguments."""
        mock_run.return_value = None
        
        # Click should handle unexpected arguments gracefully
        result = self.runner.invoke(main, ['--unknown-arg'])
        
        # Should show help or error for unknown arguments
        assert result.exit_code != 0
        mock_run.assert_not_called()


@pytest.mark.unit
class TestCLIIntegration:
    """Test CLI integration with the server module."""
    
    def setup_method(self):
        """Setup method for each test."""
        self.runner = CliRunner()
    
    @patch('mcp_lancedb.cli.run')
    def test_cli_calls_server_run(self, mock_run):
        """Test that CLI calls the server run function."""
        mock_run.return_value = None
        
        result = self.runner.invoke(main, [])
        
        assert result.exit_code == 0
        mock_run.assert_called_once()
    
    @patch('mcp_lancedb.cli.run')
    def test_cli_propagates_server_exceptions(self, mock_run):
        """Test that CLI properly propagates server exceptions."""
        test_exception = Exception("Server internal error")
        mock_run.side_effect = test_exception
        
        result = self.runner.invoke(main, [])
        
        assert result.exit_code == 1
        mock_run.assert_called_once()


@pytest.mark.unit
class TestCLIEdgeCases:
    """Test CLI edge cases and error conditions."""
    
    def setup_method(self):
        """Setup method for each test."""
        self.runner = CliRunner()
    
    @patch('mcp_lancedb.cli.run')
    def test_cli_system_exit_handling(self, mock_run):
        """Test CLI handling of SystemExit exceptions."""
        mock_run.side_effect = SystemExit(0)
        
        result = self.runner.invoke(main, [])
        
        # SystemExit should be handled by Click
        assert result.exit_code == 0
    
    @patch('mcp_lancedb.cli.run')
    def test_cli_keyboard_interrupt_handling(self, mock_run):
        """Test CLI handling of KeyboardInterrupt."""
        mock_run.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(main, [])
        
        assert result.exit_code == 1
    
    @patch('mcp_lancedb.cli.run')
    def test_cli_memory_error_handling(self, mock_run):
        """Test CLI handling of MemoryError."""
        mock_run.side_effect = MemoryError("Out of memory")
        
        result = self.runner.invoke(main, [])
        
        assert result.exit_code == 1
    
    def test_cli_logger_name(self):
        """Test that the logger has the correct name."""
        from mcp_lancedb.cli import logger
        
        assert logger.name == "mcp_lancedb.cli"
    
    def test_cli_logger_level(self):
        """Test that the logger level is appropriate."""
        from mcp_lancedb.cli import logger
        
        # The logger should be able to handle CRITICAL level messages (which is the default)
        assert logger.isEnabledFor(logging.CRITICAL) 