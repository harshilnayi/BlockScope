"""Tests for CLI tool."""
import pytest
from click.testing import CliRunner
from cli.main import cli

def test_scan_command_help():
    """Test that scan command shows help."""
    runner = CliRunner()
    result = runner.invoke(cli, ['scan', '--help'])
    
    assert result.exit_code == 0
    assert 'Scan a Solidity contract' in result.output

def test_scan_nonexistent_file():
    """Test scanning nonexistent file."""
    runner = CliRunner()
    result = runner.invoke(cli, ['scan', '/nonexistent/file.sol'])
    
    assert result.exit_code != 0
    assert 'not found' in result.output.lower()
