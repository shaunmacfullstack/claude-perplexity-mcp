# Perplexity MCP Server - Implementation Plan

## Project Overview

Build a production-quality MCP server that exposes Perplexity AI's search capabilities to Claude, enabling seamless research integration during conversations.

**Target Repository:** Public GitHub repository  
**Language:** Python 3.10+  
**Key Focus:** Security, code quality, proper error handling

---

## Security Requirements (CRITICAL)

### API Key & Secrets Management
- **NEVER hardcode API keys** - use environment variables via `python-dotenv`
- Store all secrets in `.env` file (never commit this file)
- Use `.env.example` with placeholder values only
- Validate API keys on startup without logging the full key
- In logs, only show sanitized keys: `pplx-****...a1b2` (first 4 and last 4 chars)

### Logging Security
- Never log full API keys, tokens, or credentials
- Sanitize all error messages before logging
- Don't log query contents if they might contain sensitive data
- Use format: `logger.info(f"API key loaded: {key[:4]}...{key[-4:]}")`

### Public Repository Rules
- Comprehensive `.gitignore` for all sensitive files
- All README examples use placeholder credentials
- Never commit logs containing real API calls
- Include `SECURITY.md` with responsible disclosure guidelines

---

## Phase 1: Project Setup & Foundation

### File Structure to Create

```
perplexity-mcp/
├── .env.example          # Template (PLACEHOLDERS ONLY)
├── .gitignore           # Comprehensive ignore file
├── README.md            # Setup and usage documentation
├── SECURITY.md          # Security policy
├── requirements.txt     # Pinned dependencies
├── config.py           # Configuration with validation
├── server.py           # Main MCP server
└── perplexity_client.py # Perplexity API wrapper
```

### .gitignore Contents (COMPLETE)

```gitignore
# Environment variables - NEVER COMMIT THESE
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Logs - may contain sensitive data
*.log
logs/
log/

# OS
.DS_Store
Thumbs.db
.AppleDouble
.LSOverride

# Testing
.pytest_cache/
.coverage
htmlcov/

# Secrets (redundant but explicit)
secrets/
*.key
*.pem
credentials.json
```

### requirements.txt

```
# Pin all versions for security and reproducibility
mcp>=0.1.0
httpx>=0.24.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

### .env.example

```bash
# Perplexity API Configuration
# Get your API key from: https://www.perplexity.ai/settings/api
PERPLEXITY_API_KEY=pplx-your-key-here-this-is-a-placeholder

# Model Configuration
DEFAULT_MODEL=sonar-pro

# Optional Features
CACHE_ENABLED=false
LOG_LEVEL=INFO

# Security Note: NEVER commit your actual .env file!
# Copy this to .env and add your real API key
```

### SECURITY.md

```markdown
# Security Policy

## Reporting Security Issues

If you discover a security vulnerability, please email [your-email] instead of using the issue tracker.

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact

**DO NOT include:**
- Your actual API keys
- Real credentials or tokens
- Production URLs or endpoints

## Supported Versions

Currently supporting: [version]

## Security Best Practices

- Never commit .env files
- Rotate API keys if accidentally exposed
- Use environment variables for all secrets
- Keep dependencies updated

## Security Checklist Before Committing

- [ ] `.env` is in `.gitignore` and NOT staged
- [ ] No API keys in code or comments
- [ ] `.env.example` has only placeholder values
- [ ] Error messages don't expose secrets
- [ ] Logs are sanitized
```

### README.md (Initial Structure)

```markdown
# Perplexity MCP Server

MCP server that exposes Perplexity AI's search capabilities to Claude.

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env`
3. Add your Perplexity API key to `.env`
4. Install dependencies: `pip install -r requirements.txt`
5. Run the server: `python server.py`

## Configuration

See `.env.example` for configuration options.

## Security

See `SECURITY.md` for security policies and best practices.

## Usage

[To be added after implementation]

## Troubleshooting

[To be added after implementation]
```

---

## Phase 2: Configuration Management

### config.py Implementation

Create a secure configuration manager that:
- Loads environment variables using `python-dotenv`
- Validates API key exists and has correct format
- **NEVER logs full API keys** - only sanitized versions
- Provides clear error messages without exposing secrets
- Fails fast if misconfigured

**Key functions:**
- `__init__()` - Load and validate all config
- `_validate_api_key()` - Check API key without exposing it
- `_sanitize_for_logs(key)` - Return safe version for logging

**Security requirements:**
```python
# GOOD - sanitized logging
logger.info(f"API key loaded: {key[:4]}...{key[-4:]}")

# BAD - exposes full key
logger.info(f"API key loaded: {key}")
```

**Error handling:**
```python
if not key:
    raise ValueError(
        "PERPLEXITY_API_KEY not found in environment. "
        "Copy .env.example to .env and add your API key."
    )
```

---

## Phase 3: Perplexity API Client

### perplexity_client.py Implementation

Create async wrapper for Perplexity API with:
- Async HTTP calls using `httpx`
- Proper error handling with sanitized messages
- Retry logic with exponential backoff (max 3 attempts)
- Input validation before making API calls
- Response parsing to extract answer and citations

**Key methods:**
- `search(query, model, search_focus, recency)` - Main search function
- `_make_request()` - Handle HTTP calls with retry logic
- `_parse_response()` - Extract structured data from API response
- `_validate_input()` - Validate query before sending

**Security requirements:**
- Sanitize all logs (no full API keys)
- Don't log potentially sensitive query contents
- Handle errors without exposing internal details
- Log format: `logger.info(f"Executing search (query length: {len(query)} chars)")`

**Error handling categories:**
1. **Rate limits** → Clear message with retry suggestion
2. **Invalid API key** → "API authentication failed. Check your PERPLEXITY_API_KEY."
3. **Network timeouts** → Retry with backoff, then fail clearly
4. **Malformed responses** → Log safely, raise informative error

---

## Phase 4: MCP Server Implementation

### server.py Implementation

Create MCP server that:
- Initializes using Anthropic's MCP SDK
- Exposes Perplexity search as a tool Claude can call
- Handles tool invocations securely
- Returns structured responses with citations

**Tool definition:**
```python
perplexity_search:
  - query: string (required) - The search question
  - model: string (optional) - Model to use (default from config)
  - search_focus: string (optional) - Search focus if API supports
  - recency: string (optional) - Time filter if API supports
```

**Response format to Claude:**
```json
{
  "answer": "Main synthesized answer from Perplexity",
  "citations": [
    {
      "index": 1,
      "url": "https://example.com/article",
      "title": "Article Title",
      "snippet": "Relevant excerpt from source"
    }
  ],
  "metadata": {
    "model_used": "sonar-pro",
    "search_focus": "general",
    "query_time_ms": 1234
  }
}
```

**Security requirements:**
- Validate all tool parameters before processing
- Sanitize errors before returning to Claude
- Configure logging to not expose sensitive data
- Validate URLs in citations (no javascript:, file:, etc.)

---

## Phase 5: Error Handling Strategy

### Error Categories & Responses

**1. Configuration Errors (Fail Fast)**
- Missing API key → "PERPLEXITY_API_KEY not found. Copy .env.example to .env and add your key."
- Invalid model name → "Invalid model. Available models: sonar, sonar-pro"
- Missing .env file → "Configuration file not found. See README.md for setup."

**2. API Errors (Graceful Degradation)**
- Rate limit exceeded → "Rate limit exceeded. Try again in X seconds."
- Authentication failed → "API authentication failed. Check your PERPLEXITY_API_KEY in .env"
- Network timeout → "Request timed out. Retrying... (attempt X/3)"
- Invalid request → Return Perplexity's error message (sanitized)

**3. MCP Errors (Log + User Feedback)**
- Invalid tool parameters → "Invalid parameter 'X': expected Y, got Z"
- Unexpected exceptions → Log full trace (sanitized), return generic error

### Sanitization Rules

```python
# BAD - exposes secrets
logger.error(f"Request failed with key: {self.api_key}")
raise Exception(f"Config file at {os.path.expanduser('~/.env')} not found")

# GOOD - sanitized
logger.error(f"Request failed with key: {self.api_key[:4]}...{self.api_key[-4:]}")
raise Exception("Configuration file not found. Check setup instructions.")
```

---

## Phase 6: Testing & Validation

### Pre-Implementation Tests

Before connecting to MCP:
1. Test Perplexity API calls work standalone
2. Verify config.py loads environment correctly
3. Confirm API key validation works
4. Check that logs don't expose secrets

### Integration Tests

After MCP integration:
1. Verify Claude can see and call the tool
2. Test successful search returns proper citations
3. Test error scenarios return helpful messages
4. Confirm multi-turn conversations work

### Security Tests

**Critical security checks:**
- [ ] `.env` is in `.gitignore` and cannot be committed
- [ ] API key never appears in logs (search logs for 'pplx-')
- [ ] Error messages don't expose internal paths
- [ ] `.env.example` has only placeholder values
- [ ] Can run `git diff --cached` without seeing secrets

### Edge Case Tests

- [ ] Empty query → validation error
- [ ] Very long query (1000+ chars) → handles appropriately
- [ ] Special characters in query → sanitized/escaped
- [ ] Invalid model name → clear error
- [ ] No API key in .env → helpful setup message
- [ ] Invalid API key → authentication error
- [ ] Network failure → retries then fails clearly
- [ ] Rate limit hit → informative message

---

## Phase 7: Documentation & Polish

### README.md Enhancements

Add comprehensive sections:
- **Installation** - Step-by-step setup
- **Configuration** - All environment variables explained
- **Usage Examples** - How to use with Claude
- **Troubleshooting** - Common issues and solutions
- **Security** - Link to SECURITY.md
- **Contributing** - Guidelines if accepting contributions

### Pre-Commit Checklist (Add to README)

```markdown
## Security Checklist Before Committing

Run this before every commit:

- [ ] `.env` is in `.gitignore` and NOT staged
- [ ] No API keys in code, comments, or documentation
- [ ] `.env.example` contains only placeholder values
- [ ] Error messages don't expose secrets
- [ ] Logs are sanitized
- [ ] All secrets use environment variables

Quick check: `git diff --cached` and search for 'pplx-'
```

### Code Comments

Add comments for:
- Complex logic (why, not what)
- Security-critical sections
- Non-obvious design decisions
- Workarounds or edge case handling

**Don't comment:**
- Obvious code
- What the code does (use good variable names instead)

---

## Implementation Order (Step-by-Step)

### Step 1: Project Structure
1. Create all files from Phase 1
2. Set up complete `.gitignore`
3. Create `.env.example` with placeholders only
4. Verify `.env` is properly ignored (try to commit it, should fail)

### Step 2: Security Validation
1. Create a test `.env` file with fake API key
2. Try to commit it → should be blocked by .gitignore
3. Verify `.env.example` has no real credentials

### Step 3: Configuration (config.py)
1. Implement environment variable loading
2. Implement API key validation with sanitized logging
3. Test with valid and invalid configurations
4. Verify logs never show full API key

### Step 4: API Client (perplexity_client.py)
1. Implement basic async HTTP client structure
2. Add input validation
3. Implement retry logic with exponential backoff
4. Add response parsing
5. Test manually with Perplexity API
6. Verify all errors are sanitized

### Step 5: MCP Server (server.py)
1. Set up basic MCP server structure
2. Define `perplexity_search` tool
3. Implement tool handler
4. Connect to config and client
5. Add logging (sanitized)

### Step 6: Integration Testing
1. Test server starts correctly
2. Test tool appears in Claude
3. Make test search and verify response format
4. Test with invalid inputs
5. Test error scenarios

### Step 7: Security Review
1. Search all files for API key patterns
2. Check all log statements for sanitization
3. Verify error messages don't expose secrets
4. Run through pre-commit checklist
5. Test that `.env` cannot be committed

### Step 8: Documentation
1. Complete README.md with examples
2. Add troubleshooting section
3. Document all configuration options
4. Add usage examples
5. Create CHANGELOG.md

### Step 9: Final Testing
1. Clean install in new environment
2. Follow README.md setup instructions
3. Verify everything works as documented
4. Test all error scenarios again

---

## Design Decisions to Research First

Before starting implementation, research:

1. **Perplexity API Documentation**
   - Exact endpoint URLs
   - Authentication method (Bearer token?)
   - Request/response format
   - Citation structure in responses
   - Rate limits for your tier
   - Available models and parameters

2. **MCP Server Examples**
   - Review 2-3 existing MCP servers on GitHub
   - Understand common patterns
   - Learn tool definition best practices
   - See how others handle async operations

3. **Best Practices**
   - Check for security vulnerabilities in dependencies
   - Review async/await patterns for httpx
   - Understand MCP SDK latest features

---

## Success Criteria

The implementation is complete when:

- [ ] Server starts without errors
- [ ] Claude can discover and call the `perplexity_search` tool
- [ ] Searches return properly formatted responses with citations
- [ ] All error scenarios return helpful messages
- [ ] Logs never expose API keys or secrets
- [ ] `.env` cannot be committed (blocked by .gitignore)
- [ ] README.md provides complete setup instructions
- [ ] All security checks pass
- [ ] Code has type hints and docstrings
- [ ] No hardcoded credentials anywhere

---

## Notes for Implementation

### Code Quality Standards
- Use type hints for all function parameters and returns
- Follow PEP 8 style guidelines
- Keep functions under 50 lines
- Write docstrings for all public functions
- Use meaningful variable names

### When to Ask for Help
Come back to Claude (not Cursor) when:
- Architectural decisions need discussion
- Trade-offs between approaches
- Security concerns or edge cases
- MCP integration isn't working as expected
- Need help understanding Perplexity API responses

### Testing Philosophy
- Test with real API calls early (don't mock everything)
- Verify security first, features second
- Test error paths, not just happy path
- Use actual Claude integration for validation

---

## Post-Implementation (Future Enhancements)

Only add these AFTER core functionality works:

**Priority 1:**
- Simple in-memory cache (dict with timestamp expiry)
- Request timeout configuration
- Verbose debug logging mode

**Priority 2:**
- Usage tracking (count API calls)
- Multiple Perplexity models as separate tools
- Health check endpoint

**Priority 3:**
- Persistent cache using SQLite
- Streaming responses if API supports
- Web UI for configuration

---

## Final Reminders

**Security is non-negotiable:**
- API keys are secrets - treat them like passwords
- Logs are often exposed - never log secrets
- Public repos are public - double-check before pushing
- Error messages can leak data - sanitize everything

**Start simple, iterate:**
- Get basic search working first
- Add error handling next
- Polish and optimize last
- Don't build features you don't need yet

**Good luck! 🚀**
