"""
MCP Server for Perplexity AI search integration.

Exposes Perplexity search capabilities as a tool that Claude can call
during conversations, with secure error handling and structured responses.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from mcp.server.mcpserver import MCPServer
from perplexity_client import get_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create MCP server instance
mcp = MCPServer("perplexity-search")


def validate_url(url: str) -> bool:
    """
    Validate URL to ensure it's safe (no javascript:, file:, data: schemes).

    Args:
        url: The URL to validate.

    Returns:
        bool: True if URL is safe, False otherwise.
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()

        # Only allow http, https schemes
        if scheme not in ["http", "https"]:
            logger.warning(
                f"Invalid URL scheme detected: {scheme} (URL sanitized)"
            )
            return False

        return True
    except Exception as e:
        logger.warning(f"URL validation error: {type(e).__name__}")
        return False


def sanitize_citations(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sanitize citations by validating URLs.

    Args:
        citations: List of citation dictionaries.

    Returns:
        List of sanitized citations with invalid URLs removed.
    """
    sanitized = []
    for citation in citations:
        url = citation.get("url", "")
        if validate_url(url):
            sanitized.append(citation)
        else:
            logger.warning(
                f"Removed citation with invalid URL: {url[:50]}..."
            )

    return sanitized


def sanitize_error(error: Exception) -> str:
    """
    Sanitize error messages before returning to Claude.

    Args:
        error: The exception to sanitize.

    Returns:
        str: Sanitized error message safe for client exposure.
    """
    error_type = type(error).__name__
    error_msg = str(error)

    # Don't expose internal implementation details
    if "api_key" in error_msg.lower() or "api key" in error_msg.lower():
        return (
            "API authentication failed. "
            "Check your PERPLEXITY_API_KEY configuration."
        )

    if "timeout" in error_msg.lower():
        return (
            "Request timed out. "
            "Please try again or check your network connection."
        )

    if "rate limit" in error_msg.lower():
        return (
            "Rate limit exceeded. "
            "Please wait a moment and try again."
        )

    # For other errors, return a generic message
    # Log the full error internally for debugging
    logger.error(f"Error sanitized for client: {error_type}: {error_msg}")

    return f"An error occurred: {error_type}. Please try again."


@mcp.tool()
async def perplexity_search(
    query: str,
    model: Optional[str] = None,
    search_focus: Optional[str] = None,
    recency: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search Perplexity AI for current information and receive structured responses with citations.

    Args:
        query: The search question or query (required).
        model: Model to use (optional, defaults to configured model).
        search_focus: Search focus mode - "web", "academic", or "sec" (optional).
        recency: Time filter - "hour", "day", "week", "month", or "year" (optional).

    Returns:
        Dict containing:
        - answer: Main synthesized answer from Perplexity
        - citations: List of citation objects with index, url, title, snippet
        - metadata: Dict with model_used, query_time_ms, and optional search_focus

    Raises:
        ValueError: If parameters are invalid.
    """
    # Validate required parameter
    if not query or not isinstance(query, str):
        raise ValueError("Query parameter is required and must be a string.")

    if not query.strip():
        raise ValueError("Query cannot be empty.")

    # Validate optional parameters
    if search_focus and search_focus not in ["web", "academic", "sec"]:
        raise ValueError(
            f"Invalid search_focus: {search_focus}. "
            "Must be one of: web, academic, sec"
        )

    if recency and recency not in ["hour", "day", "week", "month", "year"]:
        raise ValueError(
            f"Invalid recency: {recency}. "
            "Must be one of: hour, day, week, month, year"
        )

    # Log search attempt (without exposing query content)
    logger.info(
        f"Tool invoked: perplexity_search "
        f"(query length: {len(query)} chars, "
        f"model: {model or 'default'}, "
        f"search_focus: {search_focus or 'none'}, "
        f"recency: {recency or 'none'})"
    )

    try:
        # Get client instance
        client = get_client()

        # Execute search
        result = await client.search(
            query=query,
            model=model,
            search_focus=search_focus,
            recency=recency,
        )

        # Sanitize citations (validate URLs)
        citations = result.get("citations", [])
        sanitized_citations = sanitize_citations(citations)

        # Build response
        response: Dict[str, Any] = {
            "answer": result.get("answer", ""),
            "citations": sanitized_citations,
            "metadata": result.get("metadata", {}),
        }

        logger.info(
            f"Search completed successfully "
            f"(citations: {len(sanitized_citations)}, "
            f"answer length: {len(response['answer'])} chars)"
        )

        return response

    except ValueError as e:
        # Re-raise validation errors as-is (they're already safe)
        logger.warning(f"Validation error: {str(e)}")
        raise

    except Exception as e:
        # Sanitize all other errors before returning
        sanitized_msg = sanitize_error(e)
        logger.error(
            f"Search failed: {type(e).__name__} - {sanitized_msg}"
        )
        raise RuntimeError(sanitized_msg) from e


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting Perplexity MCP Server...")

    # Run server with stdio transport (standard for MCP)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
