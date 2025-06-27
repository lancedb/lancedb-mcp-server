#!/usr/bin/env python3
"""Test runner script for MCP LanceDB with different test categories."""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd: list, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} - PASSED")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED (exit code: {e.returncode})")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run MCP LanceDB tests")
    parser.add_argument(
        "test_type", 
        choices=["unit", "integration", "all", "fast", "slow"],
        help="Type of tests to run"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true", 
        help="Run with coverage reporting"
    )
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run tests in parallel"
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    base_cmd = ["python", "-m", "pytest"]
    
    # Add verbosity
    if args.verbose:
        base_cmd.append("-vv")
    
    # Add coverage
    if args.coverage:
        base_cmd.extend(["--cov=src/mcp_lancedb", "--cov-report=html", "--cov-report=term"])
    
    # Add parallel execution
    if args.parallel:
        base_cmd.extend(["-n", "auto"])
    
    success = True
    
    if args.test_type == "unit":
        cmd = base_cmd + ["-m", "unit", "tests/unit/"]
        success &= run_command(cmd, "Unit Tests")
        
    elif args.test_type == "integration":
        cmd = base_cmd + ["-m", "integration", "tests/integration/"]
        success &= run_command(cmd, "Integration Tests")
        
    elif args.test_type == "fast":
        cmd = base_cmd + ["-m", "unit", "tests/unit/"]
        success &= run_command(cmd, "Fast Unit Tests")
        
        cmd = base_cmd + ["-m", "integration and not slow", "tests/integration/"]
        success &= run_command(cmd, "Fast Integration Tests")
        
    elif args.test_type == "slow":
        cmd = base_cmd + ["-m", "slow", "tests/"]
        success &= run_command(cmd, "Slow Tests")
        
    elif args.test_type == "all":
        # Run unit tests first (fast feedback)
        cmd = base_cmd + ["-m", "unit", "tests/unit/"]
        success &= run_command(cmd, "Unit Tests")
        
        # Then integration tests
        cmd = base_cmd + ["-m", "integration", "tests/integration/"]
        success &= run_command(cmd, "Integration Tests")
        
        # Finally slow tests if everything else passed
        if success:
            cmd = base_cmd + ["-m", "slow", "tests/"]
            success &= run_command(cmd, "Slow Tests")
    
    # Summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Test suite completed successfully")
    else:
        print("💥 SOME TESTS FAILED!")
        print("❌ Check the output above for details")
    print(f"{'='*60}")
    
    # Coverage report location
    if args.coverage and success:
        print(f"\n📊 Coverage report generated at: htmlcov/index.html")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 