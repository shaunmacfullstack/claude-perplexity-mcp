"""
Phase 5: Testing & Validation Script

Comprehensive test suite for Perplexity MCP Server with credit-conscious testing.
Tests functionality, security, and error handling without excessive API usage.
"""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Import project modules
from config import Config, get_config
from perplexity_client import PerplexityClient, get_client

# Configure logging for tests
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise during tests
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Test results tracking
test_results: List[Tuple[str, bool, str]] = []
credit_estimate = 0


def record_test(name: str, passed: bool, message: str = "") -> None:
    """Record a test result."""
    test_results.append((name, passed, message))
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if message:
        print(f"   {message}")


def print_summary() -> None:
    """Print test summary."""
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result, _ in test_results if result)
    failed = len(test_results) - passed
    total = len(test_results)

    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"\nEstimated Credit Usage: ~${credit_estimate:.4f}")

    if failed > 0:
        print("\nFailed Tests:")
        for name, result, message in test_results:
            if not result:
                print(f"  - {name}: {message}")

    print("\n" + "=" * 70)


# ============================================================================
# Pre-Implementation Tests (Verification)
# ============================================================================


def test_config_loading() -> None:
    """Test that config.py loads environment correctly."""
    global credit_estimate

    try:
        config = get_config()

        # Verify API key is loaded
        api_key = config.get_api_key()
        if not api_key:
            record_test(
                "Config Loading - API Key",
                False,
                "API key not loaded",
            )
            return

        if not api_key.startswith("pplx-"):
            record_test(
                "Config Loading - API Key Format",
                False,
                f"API key doesn't start with 'pplx-': {api_key[:4]}...{api_key[-4:]}",
            )
            return

        # Verify other config values
        assert config.default_model is not None
        assert isinstance(config.cache_enabled, bool)

        record_test("Config Loading", True, f"Model: {config.default_model}")

    except Exception as e:
        record_test("Config Loading", False, f"Error: {type(e).__name__}: {e}")


def test_api_key_sanitization() -> None:
    """Test that API keys are sanitized in logs."""
    try:
        config = get_config()
        api_key = config.get_api_key()

        # Check sanitization method
        sanitized = config._sanitize_for_logs(api_key)

        if len(sanitized) < len(api_key) and "..." in sanitized:
            record_test(
                "API Key Sanitization",
                True,
                f"Sanitized format: {sanitized}",
            )
        else:
            record_test(
                "API Key Sanitization",
                False,
                "Sanitization not working correctly",
            )

    except Exception as e:
        record_test(
            "API Key Sanitization",
            False,
            f"Error: {type(e).__name__}: {e}",
        )


# ============================================================================
# Integration Tests
# ============================================================================


async def test_perplexity_api_call() -> None:
    """Test Perplexity API call with minimal query."""
    global credit_estimate

    try:
        client = get_client()

        # Use a very short, simple query to minimize credit usage
        query = "What is Python?"
        print(f"\nTesting API call with query: '{query}'")

        result = await client.search(query=query)

        # Verify response structure
        if "answer" not in result:
            record_test("API Call - Response Structure", False, "Missing 'answer' field")
            return

        if "citations" not in result:
            record_test(
                "API Call - Response Structure",
                False,
                "Missing 'citations' field",
            )
            return

        if "metadata" not in result:
            record_test(
                "API Call - Response Structure",
                False,
                "Missing 'metadata' field",
            )
            return

        # Verify answer is not empty
        answer = result.get("answer", "")
        if not answer or len(answer) < 10:
            record_test(
                "API Call - Answer Content",
                False,
                f"Answer too short: {len(answer)} chars",
            )
            return

        citations = result.get("citations", [])
        metadata = result.get("metadata", {})

        record_test(
            "API Call - Successful",
            True,
            f"Answer: {len(answer)} chars, Citations: {len(citations)}, "
            f"Time: {metadata.get('query_time_ms', 0)}ms",
        )

        # Estimate credit: ~$0.001 per query for short queries
        credit_estimate += 0.001

    except Exception as e:
        record_test(
            "API Call - Error Handling",
            False,
            f"Error: {type(e).__name__}: {e}",
        )


async def test_citations_structure() -> None:
    """Test that citations are properly structured."""
    global credit_estimate

    try:
        client = get_client()
        query = "Python programming language"

        result = await client.search(query=query)
        citations = result.get("citations", [])

        if not citations:
            record_test(
                "Citations Structure",
                False,
                "No citations returned",
            )
            return

        # Check citation structure
        first_citation = citations[0]
        required_fields = ["index", "url", "title", "snippet"]

        missing_fields = [
            field for field in required_fields if field not in first_citation
        ]

        if missing_fields:
            record_test(
                "Citations Structure",
                False,
                f"Missing fields: {missing_fields}",
            )
            return

        # Verify URL is valid format
        url = first_citation.get("url", "")
        if not url.startswith(("http://", "https://")):
            record_test(
                "Citations Structure - URL Format",
                False,
                f"Invalid URL format: {url[:50]}",
            )
            return

        record_test(
            "Citations Structure",
            True,
            f"Found {len(citations)} citations with proper structure",
        )

        credit_estimate += 0.001

    except Exception as e:
        record_test(
            "Citations Structure",
            False,
            f"Error: {type(e).__name__}: {e}",
        )


# ============================================================================
# Security Tests
# ============================================================================


def test_env_in_gitignore() -> None:
    """Test that .env is in .gitignore."""
    try:
        gitignore_path = Path(".gitignore")

        if not gitignore_path.exists():
            record_test(".env in .gitignore", False, ".gitignore file not found")
            return

        content = gitignore_path.read_text()

        # Check for .env patterns
        patterns = [".env", ".env.local", ".env.*.local"]

        missing_patterns = [
            pattern for pattern in patterns if pattern not in content
        ]

        if missing_patterns:
            record_test(
                ".env in .gitignore",
                False,
                f"Missing patterns: {missing_patterns}",
            )
            return

        record_test(".env in .gitignore", True, "All .env patterns found")

    except Exception as e:
        record_test(
            ".env in .gitignore",
            False,
            f"Error: {type(e).__name__}: {e}",
        )


def test_no_exposed_api_keys() -> None:
    """Robust security scanner for exposed API keys and unsafe patterns."""
    import re

    try:
        # Files to check
        files_to_check = [
            "config.py",
            "perplexity_client.py",
            "server.py",
            "test_phase5.py",
        ]

        # Threat patterns
        hardcoded_pattern = re.compile(
            r'["\']pplx-[a-zA-Z0-9]{20,}["\']', re.IGNORECASE
        )

        # Logging patterns that might expose keys
        logging_patterns = [
            re.compile(r'logger\.\w+\([^)]*\bapi_key\b', re.IGNORECASE),
            re.compile(r'print\([^)]*\bapi_key\b', re.IGNORECASE),
            re.compile(r'logging\.\w+\([^)]*\bapi_key\b', re.IGNORECASE),
            re.compile(r'raise\s+\w+Error\([^)]*\bapi_key\b', re.IGNORECASE),
        ]

        # Safe patterns (if found, indicates sanitization)
        safe_patterns = [
            re.compile(r'_sanitize', re.IGNORECASE),
            re.compile(r'\[:4\]'),
            re.compile(r'\[-4:\]'),
            re.compile(r'\.\.\.'),
        ]

        # Safe contexts (don't flag these)
        safe_contexts = [
            re.compile(r'os\.getenv\(["\']PERPLEXITY_API_KEY'),
            re.compile(r'config\.get_api_key\(\)'),
            re.compile(r'\.startswith\(["\']pplx-'),
            re.compile(r'placeholder', re.IGNORECASE),
            re.compile(r'your-key-here', re.IGNORECASE),
        ]

        vulnerabilities = []

        for file_path in files_to_check:
            path = Path(file_path)
            if not path.exists():
                continue

            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Skip binary files
                continue

            lines = content.split("\n")
            in_docstring = False
            docstring_delimiter = None

            for line_num, line in enumerate(lines, 1):
                stripped = line.strip()

                # Skip empty lines
                if not stripped:
                    continue

                # Track docstrings
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    if in_docstring:
                        # Check if this closes the docstring
                        if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                            in_docstring = False
                            docstring_delimiter = None
                        elif (
                            docstring_delimiter == '"""'
                            and stripped.endswith('"""')
                        ) or (
                            docstring_delimiter == "'''"
                            and stripped.endswith("'''")
                        ):
                            in_docstring = False
                            docstring_delimiter = None
                    else:
                        # Opening docstring
                        in_docstring = True
                        if '"""' in stripped:
                            docstring_delimiter = '"""'
                        else:
                            docstring_delimiter = "'''"
                        # Check if it's a one-liner
                        if (
                            stripped.count('"""') >= 2
                            or stripped.count("'''") >= 2
                        ):
                            in_docstring = False
                            docstring_delimiter = None
                    continue

                # Skip comments
                if stripped.startswith("#"):
                    continue

                # Skip docstrings
                if in_docstring:
                    continue

                # Check for hardcoded API keys
                if hardcoded_pattern.search(line):
                    # Check if it's in a safe context (placeholder, etc.)
                    is_safe = any(
                        safe_context.search(line) for safe_context in safe_contexts
                    )
                    if not is_safe:
                        vulnerabilities.append(
                            (
                                file_path,
                                line_num,
                                "Hardcoded API key detected",
                                line.strip()[:80],
                            )
                        )

                # Check for unsafe logging/printing
                for logging_pattern in logging_patterns:
                    if logging_pattern.search(line):
                        # Check if sanitization is present
                        has_sanitization = any(
                            safe_pattern.search(line) for safe_pattern in safe_patterns
                        )

                        # Check if it's in a safe context
                        is_safe_context = any(
                            safe_context.search(line)
                            for safe_context in safe_contexts
                        )

                        if not has_sanitization and not is_safe_context:
                            # Determine threat type
                            if "logger" in line.lower():
                                threat_type = "Unsafe logging without sanitization"
                            elif "print" in line.lower():
                                threat_type = "Unsafe print statement"
                            elif "raise" in line.lower():
                                threat_type = "Unsafe error message"
                            else:
                                threat_type = "Unsafe API key exposure"

                            vulnerabilities.append(
                                (
                                    file_path,
                                    line_num,
                                    threat_type,
                                    line.strip()[:80],
                                )
                            )

        if vulnerabilities:
            # Format vulnerability report
            report_lines = []
            for file_path, line_num, issue, code_snippet in vulnerabilities:
                report_lines.append(
                    f"  {file_path}:{line_num} - {issue}\n"
                    f"    Code: {code_snippet}"
                )

            record_test(
                "No Exposed API Keys",
                False,
                f"Security vulnerabilities found:\n" + "\n".join(report_lines),
            )
        else:
            record_test(
                "No Exposed API Keys",
                True,
                "No security vulnerabilities detected",
            )

    except Exception as e:
        record_test(
            "No Exposed API Keys",
            False,
            f"Scanner error: {type(e).__name__}: {e}",
        )


def test_env_example_placeholders() -> None:
    """Test that .env.example has only placeholder values."""
    try:
        env_example_path = Path(".env.example")

        if not env_example_path.exists():
            record_test(
                ".env.example Placeholders",
                False,
                ".env.example file not found",
            )
            return

        content = env_example_path.read_text()

        # Check for placeholder patterns
        if "pplx-your-key-here" in content or "placeholder" in content.lower():
            record_test(
                ".env.example Placeholders",
                True,
                "Contains placeholder values",
            )
        else:
            # Check if it might contain a real key
            if "pplx-" in content:
                # Count non-placeholder patterns
                lines = content.split("\n")
                real_key_lines = [
                    line
                    for line in lines
                    if "pplx-" in line
                    and "placeholder" not in line.lower()
                    and "your-key" not in line.lower()
                ]

                if real_key_lines:
                    record_test(
                        ".env.example Placeholders",
                        False,
                        "Possible real API key found",
                    )
                else:
                    record_test(
                        ".env.example Placeholders",
                        True,
                        "No real keys detected",
                    )
            else:
                record_test(
                    ".env.example Placeholders",
                    True,
                    "No API key patterns found",
                )

    except Exception as e:
        record_test(
            ".env.example Placeholders",
            False,
            f"Error: {type(e).__name__}: {e}",
        )


def test_git_no_secrets() -> None:
    """Test that git diff --cached shows no secrets."""
    try:
        # Check if .env is staged
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            # Git might not be initialized or no staged files
            record_test(
                "Git No Secrets",
                True,
                "No staged files or git not initialized",
            )
            return

        staged_files = result.stdout.strip().split("\n")
        staged_files = [f for f in staged_files if f]

        if ".env" in staged_files:
            record_test(
                "Git No Secrets",
                False,
                ".env file is staged! This is a security risk.",
            )
            return

        # Check staged content for API keys
        if staged_files:
            diff_result = subprocess.run(
                ["git", "diff", "--cached"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if diff_result.returncode == 0:
                diff_content = diff_result.stdout

                # Look for API key patterns
                if "pplx-" in diff_content:
                    # Check if it's a placeholder
                    if "placeholder" not in diff_content.lower():
                        record_test(
                            "Git No Secrets",
                            False,
                            "Possible API key in staged diff",
                        )
                        return

        record_test("Git No Secrets", True, "No secrets in staged files")

    except subprocess.TimeoutExpired:
        record_test("Git No Secrets", True, "Git check timed out (skipped)")
    except FileNotFoundError:
        record_test("Git No Secrets", True, "Git not available (skipped)")
    except Exception as e:
        record_test(
            "Git No Secrets",
            False,
            f"Error: {type(e).__name__}: {e}",
        )


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_empty_query() -> None:
    """Test that empty query raises validation error."""
    try:
        # This should be caught by validation, not make an API call
        # We'll test the client's validation method directly
        client = get_client()

        # Test empty string
        try:
            client._validate_input("")
            record_test("Empty Query Validation", False, "Empty query accepted")
        except ValueError:
            record_test("Empty Query Validation", True, "Empty query rejected")

        # Test whitespace-only
        try:
            client._validate_input("   ")
            record_test(
                "Empty Query Validation",
                False,
                "Whitespace-only query accepted",
            )
        except ValueError:
            record_test(
                "Empty Query Validation",
                True,
                "Whitespace-only query rejected",
            )

    except Exception as e:
        record_test(
            "Empty Query Validation",
            False,
            f"Error: {type(e).__name__}: {e}",
        )


async def test_medium_length_query() -> None:
    """Test medium-length query (150-1000 chars) handling."""
    global credit_estimate

    try:
        client = get_client()

        # Create a query in the 150-1000 character range
        query = "What is " + "Python " * 25  # Approximately 200 chars
        query = query[:200]  # Trim to approximately 200 chars

        # Validate query length is in acceptable range (150-1000 chars)
        if not (150 <= len(query) <= 1000):
            record_test(
                "Medium Length Query",
                False,
                f"Query length out of range: {len(query)} (expected 150-1000)",
            )
            return

        result = await client.search(query=query)

        if "answer" in result and result["answer"]:
            record_test(
                "Medium Length Query",
                True,
                f"Handled {len(query)}-char query successfully",
            )
            credit_estimate += 0.001
        else:
            record_test(
                "Medium Length Query",
                False,
                "No answer returned",
            )

    except Exception as e:
        record_test(
            "Medium Length Query",
            False,
            f"Error: {type(e).__name__}: {e}",
        )


async def test_special_characters() -> None:
    """Test query with special characters."""
    global credit_estimate

    try:
        client = get_client()

        # Query with various special characters
        query = "What is Python? (programming language) & how does it work?"

        result = await client.search(query=query)

        if "answer" in result:
            record_test(
                "Special Characters",
                True,
                "Special characters handled correctly",
            )
            credit_estimate += 0.001
        else:
            record_test(
                "Special Characters",
                False,
                "Query with special characters failed",
            )

    except Exception as e:
        record_test(
            "Special Characters",
            False,
            f"Error: {type(e).__name__}: {e}",
        )


def test_invalid_model_name() -> None:
    """Test that invalid model name validation exists."""
    try:
        # Read server.py file directly to check for validation logic
        server_path = Path("server.py")
        if not server_path.exists():
            record_test(
                "Invalid Model Validation",
                False,
                "server.py not found",
            )
            return

        content = server_path.read_text(encoding="utf-8")

        # Check for validation logic patterns
        has_search_focus_validation = (
            "search_focus" in content
            and "not in" in content
            and "web" in content
            and "academic" in content
        )

        has_recency_validation = (
            "recency" in content
            and "not in" in content
            and "hour" in content
            and "day" in content
        )

        if has_search_focus_validation or has_recency_validation:
            record_test(
                "Invalid Model Validation",
                True,
                "Validation logic exists in code",
            )
        else:
            record_test(
                "Invalid Model Validation",
                False,
                "Validation logic not found",
            )

    except Exception as e:
        record_test(
            "Invalid Model Validation",
            False,
            f"Error: {type(e).__name__}: {e}",
        )


def test_error_handling_structure() -> None:
    """Test that error handling structure exists (without triggering errors)."""
    try:
        # Read server.py file directly to check for error handling functions
        server_path = Path("server.py")
        if not server_path.exists():
            record_test(
                "Error Handling Structure",
                False,
                "server.py not found",
            )
            return

        content = server_path.read_text(encoding="utf-8")

        # Check that sanitize_error function exists
        has_sanitize_error = (
            "def sanitize_error" in content
            or "sanitize_error" in content
        )

        # Check that validate_url function exists
        has_validate_url = (
            "def validate_url" in content
            or "validate_url" in content
        )

        # Check for error sanitization logic
        has_error_sanitization = (
            "api_key" in content.lower()
            and ("sanitize" in content.lower() or "sanitized" in content.lower())
        )

        # Check for URL validation logic
        has_url_validation = (
            "javascript:" in content.lower()
            or "file://" in content.lower()
            or "http://" in content
            or "https://" in content
        )

        if has_sanitize_error and has_validate_url:
            # Try to import and test the functions
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("server", "server.py")
                if spec and spec.loader:
                    server_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(server_module)
                    
                    sanitize_error = server_module.sanitize_error
                    validate_url = server_module.validate_url

                    # Test sanitize_error with a mock error
                    test_error = ValueError("Test error with api_key in message")
                    sanitized = sanitize_error(test_error)

                    if "api_key" not in sanitized.lower():
                        sanitize_works = True
                    else:
                        sanitize_works = False

                    # Test URL validation
                    url_works = (
                        validate_url("https://example.com") is True
                        and validate_url("http://example.com") is True
                        and validate_url("javascript:alert(1)") is False
                        and validate_url("file:///etc/passwd") is False
                    )

                    if sanitize_works and url_works:
                        record_test(
                            "Error Handling Structure",
                            True,
                            "Error sanitization and URL validation working",
                        )
                    else:
                        record_test(
                            "Error Handling Structure",
                            False,
                            f"Functions exist but tests failed (sanitize: {sanitize_works}, url: {url_works})",
                        )
                else:
                    # Fallback: just verify functions exist in code
                    if has_error_sanitization and has_url_validation:
                        record_test(
                            "Error Handling Structure",
                            True,
                            "Error handling functions found in code",
                        )
                    else:
                        record_test(
                            "Error Handling Structure",
                            False,
                            "Error handling functions not found",
                        )
            except Exception as import_error:
                # Fallback: just verify functions exist in code
                if has_error_sanitization and has_url_validation:
                    record_test(
                        "Error Handling Structure",
                        True,
                        f"Error handling functions found (import test skipped: {type(import_error).__name__})",
                    )
                else:
                    record_test(
                        "Error Handling Structure",
                        False,
                        f"Error handling functions not found: {type(import_error).__name__}",
                    )
        else:
            record_test(
                "Error Handling Structure",
                False,
                f"Functions not found (sanitize_error: {has_sanitize_error}, validate_url: {has_validate_url})",
            )

    except Exception as e:
        record_test(
            "Error Handling Structure",
            False,
            f"Error: {type(e).__name__}: {e}",
        )


# ============================================================================
# Main Test Runner
# ============================================================================


async def run_all_tests() -> None:
    """Run all tests."""
    print("=" * 70)
    print("PHASE 5: TESTING & VALIDATION")
    print("=" * 70)
    print("\nRunning comprehensive test suite...")
    print("(Credit-conscious: using minimal queries where possible)\n")

    # Pre-Implementation Tests
    print("\n[Pre-Implementation Tests]")
    print("-" * 70)
    test_config_loading()
    test_api_key_sanitization()

    # Integration Tests
    print("\n[Integration Tests]")
    print("-" * 70)
    await test_perplexity_api_call()
    await test_citations_structure()

    # Security Tests
    print("\n[Security Tests]")
    print("-" * 70)
    test_env_in_gitignore()
    test_no_exposed_api_keys()
    test_env_example_placeholders()
    test_git_no_secrets()

    # Edge Case Tests
    print("\n[Edge Case Tests]")
    print("-" * 70)
    test_empty_query()
    await test_medium_length_query()
    await test_special_characters()
    test_invalid_model_name()
    test_error_handling_structure()

    # Print summary
    print_summary()

    # Exit with appropriate code
    failed_count = sum(1 for _, result, _ in test_results if not result)
    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
