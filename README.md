# Greenhouse MCP Server 🌱

An MCP (Model Context Protocol) server for interacting with the Greenhouse Harvest API. This server enables AI agents to manage recruitment workflows through Greenhouse's applicant tracking system.

## Features

The Greenhouse MCP server provides tools for:

### Jobs Management
- `list_jobs` - List all jobs with filtering options
- `get_job` - Get detailed information about a specific job
- `create_job` - Create a new job by cloning an existing template job
- `update_job` - Update job metadata (name, notes, department, offices, custom fields)
- `list_job_posts_for_job` - List the public-facing job posts attached to a job

### Candidate Management
- `list_candidates` - Search and list candidates
- `get_candidate` - Get detailed candidate information
- `create_candidate` - Add new candidates to the system
- `update_candidate` - Update existing candidate information
- `add_note_to_candidate` - Add notes to candidate profiles

### Application Tracking
- `list_applications` - List applications with filtering
- `get_application` - Get detailed application information
- `advance_application` - Move applications through hiring stages
- `reject_application` - Reject applications with reasons
- `add_note_to_application` - Add notes to applications

### Job Openings
- `list_job_openings` - List job openings across the org with status filter
- `get_job_opening` - Get a specific opening for a job
- `create_job_openings` - Add new headcount (one or many) to a job
- `update_job_opening` - Generic update (status, close reason, custom fields)
- `close_job_opening` - Convenience wrapper to close an opening with a reason
- `reopen_job_opening` - Reopen a previously closed opening
- `delete_job_opening` - Permanently delete an opening (requires `confirm=True`)
- `list_close_reasons` - List valid close reason IDs for closing openings

### Job Stages
- `list_job_stages` - List all job stages in the org
- `list_job_stages_for_job` - List the stages of a job's interview plan in order
- `get_job_stage` - Retrieve a single job stage with its interview kit

### Hiring Team
- `get_job_hiring_team` - Get a job's recruiters, coordinators, hiring managers, sourcers
- `add_hiring_team_members` - Append members to a job's hiring team
- `replace_hiring_team` - Wholesale-replace a job's hiring team
- `remove_hiring_team_member` - Remove a user from a job's hiring team

### Organization Data
- `list_departments` - List all departments
- `list_offices` - List all offices
- `list_users` - List Greenhouse users

## Installation

### Prerequisites
- Python 3.10+
- Greenhouse API key (obtain from your Greenhouse admin panel)

> **Note:** This package is not yet published to PyPI. Install from source.

### Install from source
```bash
git clone https://github.com/scevallos/greenhouse-mcp.git
cd greenhouse-mcp
pip install -e .
```

## Configuration

Create a `.env` file in your project root:

```env
GREENHOUSE_API_KEY=your_api_key_here
GREENHOUSE_USER_ID=your_greenhouse_user_id  # Required for write operations (POST/PATCH/PUT/DELETE)
GREENHOUSE_BASE_URL=https://harvest.greenhouse.io/v1  # Optional, this is the default
```

**Note:** `GREENHOUSE_USER_ID` is required for write operations (creating candidates, advancing/rejecting applications, adding notes, etc.). It is sent as the `On-Behalf-Of` header so the action is attributed to a real Greenhouse user. Find your user ID in Greenhouse under Configure > Users — the ID appears in the URL when you select a user. Each write tool also accepts an `on_behalf_of` parameter that overrides the env default for that single call.

## Usage

### Running Locally with FastMCP

```bash
# Using FastMCP CLI
fastmcp run src.greenhouse_mcp:mcp

# Or with Python directly
python -m src.greenhouse_mcp
```

### Using with Claude Desktop

Since the package is not published to PyPI, point Claude Desktop at your local clone. Replace `/absolute/path/to/greenhouse-mcp` with the directory you cloned the repo into.

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "greenhouse": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/greenhouse-mcp",
        "run",
        "python",
        "-m",
        "src.greenhouse_mcp"
      ],
      "env": {
        "GREENHOUSE_API_KEY": "your_api_key_here",
        "GREENHOUSE_USER_ID": "your_greenhouse_user_id"
      }
    }
  }
}
```

If you'd rather use the installed console script, run `pip install -e .` (or `uv pip install -e .`) inside the clone first, then use:

```json
{
  "mcpServers": {
    "greenhouse": {
      "command": "/absolute/path/to/your/venv/bin/greenhouse-mcp",
      "env": {
        "GREENHOUSE_API_KEY": "your_api_key_here",
        "GREENHOUSE_USER_ID": "your_greenhouse_user_id"
      }
    }
  }
}
```

Once the package is published to PyPI, the simpler `uvx greenhouse-mcp` form will work.

### Using with MCPD

> **Note:** The MCPD flow below assumes `greenhouse-mcp` resolves through MCPD's registry, which depends on the package being published. Until then, use the Claude Desktop instructions above.

1. Install MCPD:
```bash
npm install -g @modelcontextprotocol/mcpd
```

2. Add the server to MCPD:
```bash
mcpd add greenhouse-mcp
```

3. Configure environment variables:
```bash
mcpd config args set greenhouse-mcp --env GREENHOUSE_API_KEY=your_api_key_here --env GREENHOUSE_USER_ID=your_greenhouse_user_id
```

4. Start the MCPD daemon:
```bash
mcpd daemon
```

The server will be available at `http://localhost:8090` with API documentation at `/docs`.

## Example Usage

Once connected to an AI assistant, you can use natural language to interact with Greenhouse:

```
"List all open engineering jobs"
"Show me candidates who applied in the last week"
"Get details for candidate ID 12345"
"Add a note to application 67890 saying 'Strong technical skills, schedule second interview'"
"Advance application 11111 to the next stage"
```

## API Rate Limiting

The server automatically handles Greenhouse API rate limits:
- Maximum 50 requests per 10 seconds
- Automatic retry with exponential backoff on rate limit errors
- Respects `Retry-After` headers

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/scevallos/greenhouse-mcp.git
cd greenhouse-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Copy environment variables
cp .env.example .env
# Edit .env with your API key
```

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black src/

# Lint
ruff check src/
```

## Security Notes

- Never commit your API key to version control
- Use environment variables or secure secret management
- The server only accepts connections from localhost by default
- All API requests use HTTPS

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

MIT License - see LICENSE file for details

## Support

For issues related to:
- This MCP server: Open an issue on GitHub
- Greenhouse API: Consult [Greenhouse API documentation](https://developers.greenhouse.io/harvest.html)
- MCP Protocol: Visit [Model Context Protocol docs](https://modelcontextprotocol.io)
- FastMCP: Check [FastMCP documentation](https://github.com/jlowin/fastmcp)