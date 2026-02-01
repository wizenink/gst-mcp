"""GStreamer MCP Server - Main entry point."""

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from gst_mcp import registry, caps, pipeline, examples, docs


# Initialize GStreamer
Gst.init(None)

# Create MCP server
app = Server("gst-mcp")


# =============================================================================
# Tool Definitions
# =============================================================================

TOOLS = [
    # Registry Introspection
    Tool(
        name="list_elements",
        description="List available GStreamer elements, optionally filtered by category (source, sink, decoder, encoder, muxer, demuxer, filter, parser, other)",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by category",
                    "enum": ["source", "sink", "decoder", "encoder", "muxer", "demuxer", "filter", "parser", "other"],
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum elements to return",
                    "default": 100,
                },
            },
        },
    ),
    Tool(
        name="get_element_info",
        description="Get detailed information about a GStreamer element including properties, pads, caps templates, and signals",
        inputSchema={
            "type": "object",
            "properties": {
                "element_name": {
                    "type": "string",
                    "description": "Name of the element (e.g., videotestsrc, x264enc)",
                },
            },
            "required": ["element_name"],
        },
    ),
    Tool(
        name="list_plugins",
        description="List all installed GStreamer plugins with version and description",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_plugin_info",
        description="Get detailed information about a GStreamer plugin including its elements",
        inputSchema={
            "type": "object",
            "properties": {
                "plugin_name": {
                    "type": "string",
                    "description": "Name of the plugin",
                },
            },
            "required": ["plugin_name"],
        },
    ),
    Tool(
        name="search_elements",
        description="Search for GStreamer elements by name, description, or caps",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "search_in": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["name", "description", "caps"]},
                    "description": "Fields to search in (defaults to all)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results",
                    "default": 50,
                },
            },
            "required": ["query"],
        },
    ),
    # Caps & Negotiation
    Tool(
        name="parse_caps",
        description="Parse a GStreamer caps string and return structured information",
        inputSchema={
            "type": "object",
            "properties": {
                "caps_string": {
                    "type": "string",
                    "description": "A GStreamer caps string (e.g., video/x-raw,format=I420,width=1920)",
                },
            },
            "required": ["caps_string"],
        },
    ),
    Tool(
        name="check_caps_compatible",
        description="Check if two GStreamer caps can intersect (are compatible)",
        inputSchema={
            "type": "object",
            "properties": {
                "caps1": {"type": "string", "description": "First caps string"},
                "caps2": {"type": "string", "description": "Second caps string"},
            },
            "required": ["caps1", "caps2"],
        },
    ),
    Tool(
        name="check_elements_can_link",
        description="Check if two GStreamer elements can link based on their pad caps",
        inputSchema={
            "type": "object",
            "properties": {
                "src_element": {"type": "string", "description": "Name of the source element"},
                "sink_element": {"type": "string", "description": "Name of the sink element"},
                "src_pad_name": {"type": "string", "description": "Optional specific src pad name"},
                "sink_pad_name": {"type": "string", "description": "Optional specific sink pad name"},
            },
            "required": ["src_element", "sink_element"],
        },
    ),
    Tool(
        name="suggest_converter",
        description="Suggest converter elements to link incompatible GStreamer elements",
        inputSchema={
            "type": "object",
            "properties": {
                "src_element": {"type": "string", "description": "Name of the source element"},
                "sink_element": {"type": "string", "description": "Name of the sink element"},
            },
            "required": ["src_element", "sink_element"],
        },
    ),
    # Pipeline Tools
    Tool(
        name="validate_pipeline",
        description="Validate a GStreamer pipeline string without running it. Reports errors and suggestions. IMPORTANT: Always use this tool FIRST when the user asks for a pipeline. Present the validated pipeline to the user and wait for their explicit confirmation before running it.",
        inputSchema={
            "type": "object",
            "properties": {
                "pipeline_string": {
                    "type": "string",
                    "description": "A gst-launch style pipeline string",
                },
            },
            "required": ["pipeline_string"],
        },
    ),
    Tool(
        name="run_pipeline",
        description="Run a GStreamer pipeline. Can run synchronously with timeout or asynchronously. CRITICAL: Do NOT call this tool unless the user has EXPLICITLY confirmed they want to run the pipeline. Always use validate_pipeline first to check and present the pipeline, then wait for the user to say they want to run it before calling this tool. IMPORTANT: Always provide working_directory so output files are created in the user's workspace, not the MCP server directory.",
        inputSchema={
            "type": "object",
            "properties": {
                "pipeline_string": {
                    "type": "string",
                    "description": "A gst-launch style pipeline string",
                },
                "timeout_seconds": {
                    "type": "number",
                    "description": "Timeout in seconds for one-shot pipelines (default 5.0)",
                    "default": 5.0,
                },
                "async_mode": {
                    "type": "boolean",
                    "description": "If true, start in background and return a handle",
                    "default": False,
                },
                "working_directory": {
                    "type": "string",
                    "description": "Directory to run the pipeline in. Output files will be created here. Should be set to the user's current working directory.",
                },
            },
            "required": ["pipeline_string"],
        },
    ),
    Tool(
        name="get_pipeline_status",
        description="Get the status of a running GStreamer pipeline",
        inputSchema={
            "type": "object",
            "properties": {
                "pipeline_id": {
                    "type": "string",
                    "description": "The pipeline ID returned from run_pipeline",
                },
            },
            "required": ["pipeline_id"],
        },
    ),
    Tool(
        name="stop_pipeline",
        description="Stop a running GStreamer pipeline",
        inputSchema={
            "type": "object",
            "properties": {
                "pipeline_id": {
                    "type": "string",
                    "description": "The pipeline ID returned from run_pipeline",
                },
            },
            "required": ["pipeline_id"],
        },
    ),
    Tool(
        name="list_running_pipelines",
        description="List all currently running GStreamer pipelines",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_pipeline_graph",
        description="Generate a DOT graph representation of a GStreamer pipeline",
        inputSchema={
            "type": "object",
            "properties": {
                "pipeline_string": {
                    "type": "string",
                    "description": "A gst-launch style pipeline string",
                },
            },
            "required": ["pipeline_string"],
        },
    ),
    # Documentation & Examples
    Tool(
        name="get_examples",
        description="Get GStreamer pipeline examples by category (playback, transcoding, streaming, capture, effects, testing, analysis)",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Category to filter",
                    "enum": ["playback", "transcoding", "streaming", "capture", "effects", "testing", "analysis"],
                },
            },
        },
    ),
    Tool(
        name="fetch_online_docs",
        description="Fetch documentation from GStreamer website for an element",
        inputSchema={
            "type": "object",
            "properties": {
                "element_name": {
                    "type": "string",
                    "description": "Name of the element",
                },
            },
            "required": ["element_name"],
        },
    ),
]


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Return the list of available tools."""
    return TOOLS


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""

    # Registry Introspection
    if name == "list_elements":
        result = registry.list_elements(
            category=arguments.get("category"),
            limit=arguments.get("limit", 100),
        )
        text = f"Found {len(result)} elements"
        if arguments.get("category"):
            text += f" in category '{arguments['category']}'"
        text += ":\n\n"
        for elem in result:
            desc = elem["description"][:80] + "..." if len(elem["description"]) > 80 else elem["description"]
            text += f"- **{elem['name']}**: {desc}\n"
        return [TextContent(type="text", text=text)]

    elif name == "get_element_info":
        result = registry.get_element_info(arguments["element_name"])
        if result is None:
            return [TextContent(type="text", text=f"Element '{arguments['element_name']}' not found")]

        text = f"# {result['name']}\n\n"
        text += f"**Long Name:** {result['long_name']}\n"
        text += f"**Description:** {result['description']}\n"
        text += f"**Category:** {result['category']}\n"
        text += f"**Klass:** {result['klass']}\n"
        text += f"**Author:** {result['author']}\n"
        text += f"**Plugin:** {result['plugin']}\n"
        text += f"**Rank:** {result['rank']}\n\n"

        text += "## Pad Templates\n\n"
        for pad in result.get("pad_templates", []):
            text += f"### {pad['name']} ({pad['direction']}, {pad['presence']})\n"
            text += f"```\n{pad['caps']}\n```\n\n"

        text += "## Properties\n\n"
        for prop in result.get("properties", [])[:30]:
            text += f"- **{prop['name']}** ({prop['type']}): {prop['blurb']}\n"
            if "default" in prop:
                text += f"  - Default: {prop['default']}\n"
            if "minimum" in prop and "maximum" in prop:
                text += f"  - Range: {prop['minimum']} to {prop['maximum']}\n"

        if result.get("signals"):
            text += "\n## Signals\n\n"
            for sig in result["signals"][:20]:
                text += f"- **{sig['name']}** -> {sig['return_type']}\n"

        return [TextContent(type="text", text=text)]

    elif name == "list_plugins":
        result = registry.list_plugins()
        text = f"Found {len(result)} plugins:\n\n"
        for plugin in result:
            desc = plugin["description"][:60] + "..." if len(plugin["description"]) > 60 else plugin["description"]
            text += f"- **{plugin['name']}** v{plugin['version']}: {desc}\n"
        return [TextContent(type="text", text=text)]

    elif name == "get_plugin_info":
        result = registry.get_plugin_info(arguments["plugin_name"])
        if result is None:
            return [TextContent(type="text", text=f"Plugin '{arguments['plugin_name']}' not found")]

        text = f"# Plugin: {result['name']}\n\n"
        text += f"**Description:** {result['description']}\n"
        text += f"**Version:** {result['version']}\n"
        text += f"**License:** {result['license']}\n"
        text += f"**Source:** {result['source']}\n\n"
        text += f"## Elements ({len(result['elements'])})\n\n"
        for elem in result["elements"]:
            text += f"- **{elem['name']}**: {elem['description']}\n"
        return [TextContent(type="text", text=text)]

    elif name == "search_elements":
        result = registry.search_elements(
            query=arguments["query"],
            search_in=arguments.get("search_in"),
            limit=arguments.get("limit", 50),
        )
        text = f"Found {len(result)} elements matching '{arguments['query']}':\n\n"
        for elem in result:
            desc = elem["description"][:60] + "..." if len(elem["description"]) > 60 else elem["description"]
            text += f"- **{elem['name']}** [{elem['category']}]: {desc}\n"
        return [TextContent(type="text", text=text)]

    # Caps & Negotiation
    elif name == "parse_caps":
        result = caps.parse_caps(arguments["caps_string"])
        if not result.get("valid"):
            return [TextContent(type="text", text=f"Invalid caps: {result.get('error', 'Unknown error')}")]

        text = "# Caps Analysis\n\n"
        text += f"**Fixed:** {result['is_fixed']}\n"
        text += f"**Any:** {result['is_any']}\n"
        text += f"**Empty:** {result['is_empty']}\n\n"
        text += "## Structures\n\n"
        for struct in result.get("structures", []):
            text += f"### {struct['name']}\n"
            for field, value in struct.get("fields", {}).items():
                text += f"- **{field}:** {value}\n"
            text += "\n"
        return [TextContent(type="text", text=text)]

    elif name == "check_caps_compatible":
        result = caps.check_caps_compatible(arguments["caps1"], arguments["caps2"])
        if "error" in result:
            return [TextContent(type="text", text=f"Error: {result['error']}")]

        text = "# Caps Compatibility\n\n"
        text += f"**Compatible:** {'Yes' if result['compatible'] else 'No'}\n\n"
        if result.get("intersection"):
            text += f"## Intersection\n\n```\n{result['intersection']}\n```\n"
        return [TextContent(type="text", text=text)]

    elif name == "check_elements_can_link":
        result = caps.check_elements_can_link(
            arguments["src_element"],
            arguments["sink_element"],
            arguments.get("src_pad_name"),
            arguments.get("sink_pad_name"),
        )
        if "error" in result:
            return [TextContent(type="text", text=f"Error: {result['error']}")]

        text = f"# Link Check: {arguments['src_element']} -> {arguments['sink_element']}\n\n"
        text += f"**Can Link:** {'Yes' if result['can_link'] else 'No'}\n\n"
        if result["compatible_pads"]:
            text += "## Compatible Pad Pairs\n\n"
            for pair in result["compatible_pads"]:
                text += f"### {pair['src_pad']} -> {pair['sink_pad']}\n"
                src_caps = pair['src_caps'][:100] + "..." if len(pair['src_caps']) > 100 else pair['src_caps']
                sink_caps = pair['sink_caps'][:100] + "..." if len(pair['sink_caps']) > 100 else pair['sink_caps']
                text += f"**Src caps:** `{src_caps}`\n"
                text += f"**Sink caps:** `{sink_caps}`\n\n"
        return [TextContent(type="text", text=text)]

    elif name == "suggest_converter":
        result = caps.suggest_converter(arguments["src_element"], arguments["sink_element"])
        if result.get("direct_link_possible"):
            return [TextContent(type="text", text=result["message"])]

        if "error" in result:
            return [TextContent(type="text", text=f"Error: {result['error']}")]

        text = f"# Converter Suggestions\n\n"
        text += f"**Source output types:** {', '.join(result.get('src_output_types', []))}\n"
        text += f"**Sink input types:** {', '.join(result.get('sink_input_types', []))}\n\n"
        text += "## Suggestions\n\n"
        for i, suggestion in enumerate(result.get("suggestions", []), 1):
            text += f"### Option {i}: {suggestion['reason']}\n"
            text += f"**Pipeline:** `{suggestion['pipeline']}`\n\n"
        return [TextContent(type="text", text=text)]

    # Pipeline Tools
    elif name == "validate_pipeline":
        result = pipeline.validate_pipeline(arguments["pipeline_string"])
        text = f"# Pipeline Validation\n\n"
        text += f"**Pipeline:** `{arguments['pipeline_string']}`\n\n"
        text += f"**Valid:** {'Yes' if result['valid'] else 'No'}\n\n"

        if result["errors"]:
            text += "## Errors\n\n"
            for error in result["errors"]:
                text += f"- {error}\n"

        if result["warnings"]:
            text += "\n## Warnings\n\n"
            for warning in result["warnings"]:
                text += f"- {warning}\n"

        if result["suggestions"]:
            text += "\n## Suggestions\n\n"
            for suggestion in result["suggestions"]:
                text += f"- {suggestion}\n"

        if result["elements"]:
            text += "\n## Elements\n\n"
            for elem in result["elements"]:
                text += f"- {elem['name']} ({elem['factory']})\n"

        return [TextContent(type="text", text=text)]

    elif name == "run_pipeline":
        result = pipeline.run_pipeline(
            arguments["pipeline_string"],
            timeout_seconds=arguments.get("timeout_seconds", 5.0),
            async_mode=arguments.get("async_mode", False),
            working_directory=arguments.get("working_directory"),
        )
        text = f"# Pipeline Execution\n\n"
        text += f"**Success:** {'Yes' if result.get('success') else 'No'}\n"
        if result.get("pipeline_id"):
            text += f"**Pipeline ID:** {result['pipeline_id']}\n"
        if result.get("error"):
            text += f"**Error:** {result['error']}\n"
        if result.get("status"):
            text += f"**Status:** {result['status']}\n"
        if result.get("messages"):
            text += "\n## Messages\n\n"
            for msg in result["messages"]:
                text += f"- {msg}\n"
        return [TextContent(type="text", text=text)]

    elif name == "get_pipeline_status":
        result = pipeline.get_pipeline_status(arguments["pipeline_id"])
        if not result.get("found"):
            return [TextContent(type="text", text=f"Pipeline '{arguments['pipeline_id']}' not found")]

        text = f"# Pipeline Status: {arguments['pipeline_id']}\n\n"
        text += f"**State:** {result['state']}\n"
        if result.get("error"):
            text += f"**Error:** {result['error']}\n"
        if result.get("recent_messages"):
            text += "\n## Recent Messages\n\n"
            for msg in result["recent_messages"]:
                text += f"- {msg}\n"
        return [TextContent(type="text", text=text)]

    elif name == "stop_pipeline":
        result = pipeline.stop_pipeline(arguments["pipeline_id"])
        if result.get("success"):
            return [TextContent(type="text", text=f"Pipeline '{arguments['pipeline_id']}' stopped")]
        return [TextContent(type="text", text=f"Error: {result.get('error', 'Unknown error')}")]

    elif name == "list_running_pipelines":
        result = pipeline.list_running_pipelines()
        if not result:
            return [TextContent(type="text", text="No pipelines currently running")]
        text = "# Running Pipelines\n\n"
        for p in result:
            text += f"- **{p['pipeline_id']}** ({p['state']}): `{p['pipeline_string']}`\n"
        return [TextContent(type="text", text=text)]

    elif name == "get_pipeline_graph":
        result = pipeline.get_pipeline_graph(arguments["pipeline_string"])
        if "error" in result:
            return [TextContent(type="text", text=f"Error: {result['error']}")]
        text = f"# Pipeline Graph\n\n{result['message']}\n\n```dot\n{result['dot']}\n```"
        return [TextContent(type="text", text=text)]

    # Documentation & Examples
    elif name == "get_examples":
        result = examples.get_examples(arguments.get("category"))
        if "error" in result:
            text = f"Error: {result['error']}\n\nAvailable: {', '.join(result['available_categories'])}"
            return [TextContent(type="text", text=text)]

        text = "# GStreamer Pipeline Examples\n\n"
        if arguments.get("category"):
            text += f"## {arguments['category'].title()}\n\n"
            for ex in result["examples"]:
                text += f"### {ex['name']}\n{ex['description']}\n\n"
                text += f"```bash\ngst-launch-1.0 {ex['pipeline']}\n```\n\n"
                text += f"*{ex['notes']}*\n\n"
        else:
            text += f"**Categories:** {', '.join(result['categories'])}\n\n"
            text += "Use `get_examples(category='<name>')` to get examples for a specific category.\n"
        return [TextContent(type="text", text=text)]

    elif name == "fetch_online_docs":
        result = await docs.fetch_online_docs(arguments["element_name"])
        if not result.get("found"):
            local_result = docs.get_element_docs_local(arguments["element_name"])
            if local_result.get("found"):
                text = f"# {arguments['element_name']} (Local Documentation)\n\n"
                text += f"**Description:** {local_result['description']}\n"
                text += f"**Klass:** {local_result['klass']}\n"
                text += f"**Author:** {local_result['author']}\n"
                text += f"\n*Online docs not found. {result.get('suggestion', '')}*"
                return [TextContent(type="text", text=text)]
            return [TextContent(type="text", text=f"Documentation not found for '{arguments['element_name']}'")]

        text = f"# {arguments['element_name']}\n\n**Source:** {result['url']}\n\n{result['content']}"
        return [TextContent(type="text", text=text)]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Run the GStreamer MCP server."""
    import asyncio

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
