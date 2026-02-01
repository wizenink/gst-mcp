# gst-mcp

[![PyPI version](https://badge.fury.io/py/gst-mcp.svg)](https://badge.fury.io/py/gst-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

MCP server for GStreamer introspection and pipeline development. Helps LLMs understand GStreamer elements, caps, and pipeline construction.

## Installation

### From PyPI (recommended)

```bash
# Using uvx (no install needed)
uvx gst-mcp

# Or install globally
uv tool install gst-mcp

# Or with pip
pip install gst-mcp
```

### From source

```bash
git clone https://github.com/wizenink/gst-mcp
cd gst-mcp
uv sync
```

### System Requirements

- Python 3.13+
- GStreamer 1.0 with development files
- PyGObject (GStreamer Python bindings)

On Arch Linux:

```bash
sudo pacman -S gstreamer gst-plugins-base gst-plugins-good python-gobject
```

On Ubuntu/Debian:

```bash
sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good python3-gi
```

## Usage with Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "gstreamer": {
      "command": "uvx",
      "args": ["gst-mcp"]
    }
  }
}
```

Or if installed from source:

```json
{
  "mcpServers": {
    "gstreamer": {
      "command": "uv",
      "args": ["--directory", "/path/to/gst-mcp", "run", "gst-mcp"]
    }
  }
}
```

## Available Tools

### Registry Introspection

- `list_elements` - List elements by category (source, sink, decoder, encoder, muxer, demuxer, filter, parser)
- `get_element_info` - Get detailed element info (properties, pads, caps templates, signals)
- `list_plugins` - List all installed GStreamer plugins
- `get_plugin_info` - Get plugin details and its elements
- `search_elements` - Search elements by name, description, or caps

### Caps & Negotiation

- `parse_caps` - Parse caps string to structured info
- `check_caps_compatible` - Check if two caps can intersect
- `check_elements_can_link` - Check if elements can link based on pad caps
- `suggest_converter` - Suggest converter elements for incompatible elements

### Pipeline Tools

- `validate_pipeline` - Validate pipeline syntax with error suggestions
- `run_pipeline` - Execute pipeline (sync with timeout or async)
- `get_pipeline_status` - Get status of running pipeline
- `stop_pipeline` - Stop a running pipeline
- `list_running_pipelines` - List all running pipelines
- `get_pipeline_graph` - Generate DOT graph of pipeline

### Documentation & Examples

- `get_examples` - Pipeline examples by category (playback, transcoding, streaming, capture, effects, testing, analysis)
- `fetch_online_docs` - Fetch element documentation from GStreamer website

## Example Queries

Ask Claude:

- "What elements can decode H.264 video?"
- "Can I link videotestsrc directly to x264enc?"
- "How do I create a pipeline to transcode MP4 to WebM?"
- "What properties does the compositor element have?"
- "Show me examples of RTMP streaming pipelines"

## License

MIT
