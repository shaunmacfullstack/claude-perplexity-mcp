"""
Perplexity API client for MCP server.

Provides async wrapper for Perplexity AI's search capabilities with
secure error handling, retry logic, and sanitized logging.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
import httpx
from config import get_config

# Configure logger
logger = logging.getLogger(__name__)

# Perplexity API endpoint
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

# Maximum query length (safety limit)
MAX_QUERY_LENGTH = 10000

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0  # seconds
RETRY_BACKOFF_MULTIPLIER = 2.0


class PerplexityClient:
    """Async client for Perplexity AI API with secure error handling."""

    def __init__(self) -> None:
        """Initialize Perplexity API client with configuration."""
        self.config = get_config()
        self.api_key = self.config.get_api_key()
        self.default_model = self.config.default_model
        self.timeout = 60.0  # seconds

        # Create HTTP client with timeout
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        logger.info(
            f"Perplexity client initialized with model: {self.default_model}"
        )

    async def search(
        self,
        query: str,
        model: Optional[str] = None,
        search_focus: Optional[str] = None,
        recency: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a search query using Perplexity API.

        Args:
            query: The search question/query.
            model: Model to use (defaults to config default).
            search_focus: Search focus mode (optional).
            recency: Recency filter (optional).

        Returns:
            Dict containing answer, citations, and metadata.

        Raises:
            ValueError: If query is invalid.
            RuntimeError: If API request fails after retries.
        """
        # Validate input before making API call
        self._validate_input(query)

        model = model or self.default_model

        # Log search attempt (without exposing query content)
        logger.info(
            f"Executing search (query length: {len(query)} chars, "
            f"model: {model})"
        )

        # Prepare request payload
        payload = self._build_payload(query, model, search_focus, recency)

        # Make request with retry logic
        start_time = time.time()
        response_data = await self._make_request(payload)
        query_time_ms = int((time.time() - start_time) * 1000)

        # Parse response
        result = self._parse_response(response_data, model, query_time_ms)

        logger.info(
            f"Search completed successfully (query_time_ms: {query_time_ms}, "
            f"citations: {len(result.get('citations', []))})"
        )

        return result

    def _validate_input(self, query: str) -> None:
        """
        Validate query input before sending to API.

        Args:
            query: The query to validate.

        Raises:
            ValueError: If query is invalid.
        """
        if not isinstance(query, str):
            raise ValueError("Query must be a string.")

        if not query.strip():
            raise ValueError("Query cannot be empty.")

        if len(query) > MAX_QUERY_LENGTH:
            raise ValueError(
                f"Query too long (max {MAX_QUERY_LENGTH} characters). "
                f"Got {len(query)} characters."
            )

    def _build_payload(
        self,
        query: str,
        model: str,
        search_focus: Optional[str],
        recency: Optional[str],
    ) -> Dict[str, Any]:
        """
        Build API request payload.

        Args:
            query: The search query.
            model: Model to use.
            search_focus: Optional search focus mode.
            recency: Optional recency filter.

        Returns:
            Dict containing request payload.
        """
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": query,
                }
            ],
            "max_tokens": 4096,
        }

        # Add search options if provided
        web_search_options: Dict[str, Any] = {}

        if recency:
            web_search_options["search_recency_filter"] = recency

        if search_focus:
            # Map search_focus to search_mode if needed
            if search_focus in ["web", "academic", "sec"]:
                payload["search_mode"] = search_focus

        if web_search_options:
            payload["web_search_options"] = web_search_options

        return payload

    async def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make HTTP request to Perplexity API with retry logic.

        Args:
            payload: Request payload.

        Returns:
            Dict containing API response data.

        Raises:
            RuntimeError: If request fails after all retries.
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug(
                    f"API request attempt {attempt}/{MAX_RETRIES}"
                )

                response = await self.client.post(
                    PERPLEXITY_API_URL,
                    json=payload,
                )

                # Handle HTTP errors
                if response.status_code == 200:
                    return response.json()

                elif response.status_code == 401:
                    # Authentication failed
                    raise RuntimeError(
                        "API authentication failed. "
                        "Check your PERPLEXITY_API_KEY in .env"
                    )

                elif response.status_code == 429:
                    # Rate limit exceeded
                    retry_after = response.headers.get("Retry-After", "unknown")
                    error_msg = (
                        f"Rate limit exceeded. "
                        f"Retry after: {retry_after} seconds"
                    )

                    if attempt < MAX_RETRIES:
                        logger.warning(f"{error_msg}. Retrying...")
                        await self._wait_before_retry(attempt)
                        continue
                    else:
                        raise RuntimeError(error_msg)

                elif response.status_code >= 500:
                    # Server error - retry
                    error_msg = (
                        f"Server error (status {response.status_code}). "
                        "Retrying..."
                    )
                    logger.warning(error_msg)

                    if attempt < MAX_RETRIES:
                        await self._wait_before_retry(attempt)
                        continue
                    else:
                        raise RuntimeError(
                            f"Server error after {MAX_RETRIES} attempts: "
                            f"status {response.status_code}"
                        )

                else:
                    # Other client errors
                    try:
                        error_data = response.json()
                        error_message = error_data.get(
                            "error", {}
                        ).get("message", "Unknown error")
                    except Exception:
                        error_message = f"HTTP {response.status_code}"

                    raise RuntimeError(
                        f"API request failed: {error_message}"
                    )

            except httpx.TimeoutException as e:
                last_error = e
                error_msg = f"Request timed out (attempt {attempt}/{MAX_RETRIES})"

                if attempt < MAX_RETRIES:
                    logger.warning(f"{error_msg}. Retrying...")
                    await self._wait_before_retry(attempt)
                else:
                    raise RuntimeError(
                        f"Request timed out after {MAX_RETRIES} attempts"
                    )

            except httpx.NetworkError as e:
                last_error = e
                error_msg = (
                    f"Network error (attempt {attempt}/{MAX_RETRIES}): "
                    f"{str(e)[:100]}"
                )

                if attempt < MAX_RETRIES:
                    logger.warning(f"{error_msg}. Retrying...")
                    await self._wait_before_retry(attempt)
                else:
                    raise RuntimeError(
                        f"Network error after {MAX_RETRIES} attempts"
                    )

            except RuntimeError:
                # Re-raise RuntimeErrors (they're already formatted)
                raise

            except Exception as e:
                last_error = e
                error_msg = (
                    f"Unexpected error (attempt {attempt}/{MAX_RETRIES}): "
                    f"{type(e).__name__}"
                )

                if attempt < MAX_RETRIES:
                    logger.warning(f"{error_msg}. Retrying...")
                    await self._wait_before_retry(attempt)
                else:
                    raise RuntimeError(
                        f"Request failed after {MAX_RETRIES} attempts: "
                        f"{type(e).__name__}"
                    )

        # Should never reach here, but handle just in case
        raise RuntimeError(
            f"Request failed after {MAX_RETRIES} attempts: {last_error}"
        )

    async def _wait_before_retry(self, attempt: int) -> None:
        """
        Wait before retrying with exponential backoff.

        Args:
            attempt: Current attempt number (1-indexed).
        """
        delay = INITIAL_RETRY_DELAY * (
            RETRY_BACKOFF_MULTIPLIER ** (attempt - 1)
        )
        logger.debug(f"Waiting {delay:.2f}s before retry...")
        await asyncio.sleep(delay)

    def _parse_response(
        self, response_data: Dict[str, Any], model: str, query_time_ms: int
    ) -> Dict[str, Any]:
        """
        Parse API response and extract structured data.

        Args:
            response_data: Raw API response data.
            model: Model used for the request.
            query_time_ms: Query execution time in milliseconds.

        Returns:
            Dict containing answer, citations, and metadata.

        Raises:
            RuntimeError: If response is malformed.
        """
        try:
            # Extract answer from choices
            choices = response_data.get("choices", [])
            if not choices:
                raise RuntimeError("No choices in API response")

            message = choices[0].get("message", {})
            answer = message.get("content", "")

            if not answer:
                raise RuntimeError("No content in API response")

            # Extract citations
            citations: List[Dict[str, Any]] = []
            search_results = response_data.get("search_results", [])

            for idx, result in enumerate(search_results, start=1):
                citation = {
                    "index": idx,
                    "url": result.get("url", ""),
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                }
                citations.append(citation)

            # Also check citations array if present
            citations_array = response_data.get("citations", [])
            if citations_array and not citations:
                # If we have citations array but no search_results,
                # create citations from the array
                for idx, citation_url in enumerate(citations_array, start=1):
                    citations.append(
                        {
                            "index": idx,
                            "url": citation_url,
                            "title": "",
                            "snippet": "",
                        }
                    )

            # Replace [1], [2] etc. with inline markdown links
            # This keeps citations inline and contextual where they were originally cited
            for citation in citations:
                index = citation.get("index")
                url = citation.get("url", "")
                title = citation.get("title", "").strip()
                
                if url and index:
                    # Use title if available, otherwise extract domain from URL
                    if title:
                        link_text = title
                    else:
                        # Extract domain as fallback
                        try:
                            link_text = url.split("/")[2] if "/" in url else url
                        except IndexError:
                            link_text = url
                    
                    # Replace [1] with ([Title](URL)) inline
                    answer = answer.replace(
                        f"[{index}]",
                        f"([{link_text}]({url}))"
                    )

            # Build result
            result: Dict[str, Any] = {
                "answer": answer,
                "citations": citations,
                "metadata": {
                    "model_used": model,
                    "query_time_ms": query_time_ms,
                },
            }

            # Add search_focus if available
            if "search_mode" in response_data:
                result["metadata"]["search_focus"] = response_data[
                    "search_mode"
                ]

            return result

        except KeyError as e:
            raise RuntimeError(
                f"Malformed API response: missing key '{e}'"
            )
        except Exception as e:
            raise RuntimeError(
                f"Error parsing API response: {type(e).__name__}: {str(e)}"
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info("Perplexity client closed")

    async def __aenter__(self) -> "PerplexityClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


# Global client instance (lazy initialization)
_client: Optional[PerplexityClient] = None


def get_client() -> PerplexityClient:
    """
    Get the global Perplexity client instance.

    Returns:
        PerplexityClient: The client instance.
    """
    global _client
    if _client is None:
        _client = PerplexityClient()
    return _client
