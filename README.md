# Perplexity MCP Server

MCP server that exposes Perplexity AI's search capabilities to Claude, enabling seamless research integration during conversations.

## 🚧 Development Status

**Current Version:** v0.1.0-alpha (In Active Development)

### ✅ Completed
- Project foundation and security setup
- Configuration management with API key validation
- Perplexity API client with retry logic and error handling
- MCP server implementation with FastMCP
- Comprehensive testing suite
- Security validation and sanitisation

### 🔮 Planned (Future Phases)
- Perplexity Spaces integration
- Memory and context management
- Thread summarisation across Spaces
- Cross-platform data synthesis
- Document generation from multi-source data

**Note:** This project is in early development. The API and features may change.

---

## Installation

### Prerequisites

- Python 3.10 or higher
- Perplexity API key ([Get one here](https://www.perplexity.ai/settings/api))
- Claude Desktop or Claude Code with MCP support

### Step-by-Step Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/claude-perplexity-mcp-server.git
   cd claude-perplexity-mcp-server
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add your Perplexity API key
   # PERPLEXITY_API_KEY=pplx-your-actual-api-key-here
   ```

5. **Verify configuration**
   ```bash
   python -c "from config import get_config; print('Configuration loaded successfully')"
   ```

6. **Test the server** (optional)
   ```bash
   python server.py
   ```

## Configuration

All configuration is managed through environment variables in the `.env` file. See `.env.example` for the template.

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PERPLEXITY_API_KEY` | Yes | - | Your Perplexity API key (starts with `pplx-`) |
| `DEFAULT_MODEL` | No | `sonar-pro` | Default Perplexity model to use |
| `CACHE_ENABLED` | No | `false` | Enable caching (future feature) |
| `LOG_LEVEL` | No | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Model Options

- `sonar` - Standard model
- `sonar-pro` - Enhanced model with better reasoning (recommended)

### Search Focus Options

- `web` - General web search (default)
- `academic` - Academic and research sources
- `sec` - Security-focused sources

### Recency Filters

- `hour` - Last hour
- `day` - Last day
- `week` - Last week
- `month` - Last month
- `year` - Last year

## Usage

### Setting Up Claude Desktop

1. **Locate Claude Desktop configuration**
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

2. **Add MCP server configuration**
   ```json
   {
     "mcpServers": {
       "perplexity-search": {
         "command": "python",
         "args": ["C:/path/to/claude-perplexity-mcp-server/server.py"],
         "env": {
           "PERPLEXITY_API_KEY": "pplx-your-key-here"
         }
       }
     }
   }
   ```

   **Note:** For Windows, use forward slashes or escaped backslashes in the path:
   ```json
   "args": ["C:\\Users\\YourName\\path\\to\\server.py"]
   ```

3. **Restart Claude Desktop**

4. **Verify the tool is available**
   - The `perplexity_search` tool should appear in Claude's available tools
   - You can ask Claude: "What tools do you have available?"

### Using the Tool

Simply ask Claude to search for information:

```
"Search Perplexity for the latest developments in quantum computing"
```

Or be more specific:

```
"Use perplexity_search to find recent news about Python 3.12 features"
```

### Tool Parameters

Claude can use these parameters when calling the tool:

- **query** (required): Your search question
- **model** (optional): Override default model (`sonar` or `sonar-pro`)
- **search_focus** (optional): `web`, `academic`, or `sec`
- **recency** (optional): `hour`, `day`, `week`, `month`, or `year`

### Example Queries

- "What are the latest AI developments?"
- "Search for recent research on climate change solutions"
- "Find current information about the Python programming language"

## Known Limitations

### Citation Display Issues

**Current Status:** Citations are included in the tool response but may not display correctly in Claude Desktop's UI.

- **Raw JSON:** Citations appear correctly in the raw tool response JSON
- **Text Display:** Citation markers and links may not render in Claude Desktop's text output
- **Workaround:** Check the raw tool response in Claude Desktop's developer tools or JSON view

**We are actively working on resolving this limitation.** This is a known issue with how Claude Desktop handles MCP tool responses and citation formatting.

### Other Limitations

- Rate limits apply based on your Perplexity API tier
- Network timeouts may occur with slow connections (automatic retry with backoff)
- Very long queries (>10,000 characters) are rejected for safety

## Troubleshooting

### Server Won't Start

**Problem:** `ModuleNotFoundError: No module named 'mcp'`

**Solution:**
```bash
pip install -r requirements.txt
```

**Problem:** `ValueError: PERPLEXITY_API_KEY not found`

**Solution:**
- Ensure `.env` file exists in the project root
- Verify `PERPLEXITY_API_KEY` is set in `.env`
- Check that the API key starts with `pplx-`

### Tool Not Appearing in Claude Desktop

**Problem:** Tool doesn't show up in Claude Desktop

**Solutions:**
1. Verify the path in `claude_desktop_config.json` is correct
2. Ensure Python is in your system PATH
3. Check that `server.py` is executable
4. Restart Claude Desktop completely
5. Check Claude Desktop logs for errors

### API Errors

**Problem:** `API authentication failed`

**Solution:**
- Verify your API key is correct in `.env`
- Ensure the API key hasn't expired
- Check your Perplexity account for API usage limits

**Problem:** `Rate limit exceeded`

**Solution:**
- Wait a few moments and try again
- Check your Perplexity API tier and rate limits
- Consider upgrading your Perplexity plan if needed

### Network Issues

**Problem:** `Request timed out`

**Solution:**
- Check your internet connection
- Verify Perplexity API is accessible from your network
- Try again (automatic retry with exponential backoff)

### Configuration Issues

**Problem:** Invalid model or parameter errors

**Solution:**
- Check `.env.example` for valid options
- Verify `DEFAULT_MODEL` is set to `sonar` or `sonar-pro`
- Ensure `search_focus` values are: `web`, `academic`, or `sec`
- Ensure `recency` values are: `hour`, `day`, `week`, `month`, or `year`

## Security

### Best Practices

- **Never commit `.env` files** - They contain sensitive API keys
- **Use environment variables** - All secrets are loaded from `.env`
- **Sanitised logging** - API keys are never logged in full
- **URL validation** - Citations are validated to prevent malicious URLs

### Security Checklist Before Committing

Run this before every commit:

- [ ] `.env` is in `.gitignore` and NOT staged
- [ ] No API keys in code, comments, or documentation
- [ ] `.env.example` contains only placeholder values
- [ ] Error messages don't expose secrets
- [ ] Logs are sanitised
- [ ] All secrets use environment variables

**Quick check:** `git diff --cached` and search for `pplx-`

See [SECURITY.md](SECURITY.md) for detailed security policies and responsible disclosure guidelines.

## Development

### Running Tests

```bash
python test_phase5.py
```

### Project Structure

```
claude-perplexity-mcp-server/
├── .env.example          # Configuration template
├── .gitignore           # Git ignore rules
├── README.md            # This file
├── SECURITY.md          # Security policy
├── requirements.txt     # Python dependencies
├── config.py           # Configuration management
├── perplexity_client.py # Perplexity API client
├── server.py           # MCP server implementation
└── test_phase5.py      # Test suite
```

### Code Quality

- Type hints throughout
- Comprehensive error handling
- Security-first design
- PEP 8 compliant
- Docstrings for all public functions

## Contributing

Contributions are welcome! Please ensure:

1. Code follows existing style and patterns
2. All tests pass
3. Security checklist is followed
4. Documentation is updated
5. Type hints are included

## License

Apache 2.0 License - see LICENSE file for details.

## Support

For issues, questions, or contributions:

- **Security issues:** See [SECURITY.md](SECURITY.md)
- **Bug reports:** Open an issue on GitHub
- **Feature requests:** Open an issue with the `enhancement` label

## Acknowledgements

- Built with [FastMCP](https://gofastmcp.com/) - High-level MCP SDK
- Powered by [Perplexity AI](https://www.perplexity.ai/) - AI-powered search
- Designed for [Claude Desktop](https://claude.ai/) - Anthropic's AI assistant
