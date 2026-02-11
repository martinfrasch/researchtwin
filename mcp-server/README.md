# mcp-server-researchtwin

MCP server for **ResearchTwin** — inter-agentic research discovery across a federated network of researcher digital twins.

Exposes the [ResearchTwin](https://researchtwin.net) platform API as [Model Context Protocol](https://modelcontextprotocol.io) tools, enabling AI agents to discover researchers, explore publications, datasets, repositories, and compute S-Index impact metrics.

## Tools

| Tool | Description |
|------|-------------|
| `list_researchers` | List all researchers registered on the platform |
| `get_profile` | Get a researcher's profile with S-Index score |
| `get_context` | Get comprehensive research context with all data source metrics |
| `get_papers` | Get publications with citation counts |
| `get_datasets` | Get datasets with QIC (Quality × Impact × Collaboration) scores |
| `get_repos` | Get code repositories with QIC scores |
| `discover` | Search across all researchers for papers, datasets, or repos |
| `get_network_map` | Get geographic affiliations for all researchers |

## Resources

| URI | Description |
|-----|-------------|
| `researchtwin://about` | Platform information and available tools |

## Installation

```bash
pip install mcp-server-researchtwin
```

Or install from source:

```bash
git clone https://github.com/martinfrasch/researchtwin.git
cd researchtwin/mcp-server
pip install -e .
```

## Usage

### Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "researchtwin": {
      "command": "mcp-server-researchtwin"
    }
  }
}
```

### Claude Code

Add to your Claude Code MCP settings:

```json
{
  "mcpServers": {
    "researchtwin": {
      "command": "mcp-server-researchtwin"
    }
  }
}
```

### Custom base URL

To point at a local or self-hosted ResearchTwin instance:

```bash
RESEARCHTWIN_URL=http://localhost:8000 mcp-server-researchtwin
```

Or in Claude Desktop config:

```json
{
  "mcpServers": {
    "researchtwin": {
      "command": "mcp-server-researchtwin",
      "env": {
        "RESEARCHTWIN_URL": "http://localhost:8000"
      }
    }
  }
}
```

## Example conversations

Once connected, you can ask your AI agent:

- *"Who are the researchers on ResearchTwin?"*
- *"Show me Martin Frasch's publications and S-Index score"*
- *"Find all datasets related to fetal monitoring"*
- *"What repositories have the highest QIC scores?"*
- *"Show me the geographic distribution of the research network"*

## Requirements

- Python 3.10+
- Network access to `researchtwin.net` (or your configured instance)

## License

MIT
