"""GStreamer documentation fetching utilities."""

import re
from typing import Any

import httpx


GSTREAMER_DOCS_BASE = "https://gstreamer.freedesktop.org/documentation"


async def fetch_online_docs(element_name: str) -> dict[str, Any]:
    """Fetch documentation for an element from GStreamer website.

    Args:
        element_name: Name of the element

    Returns:
        Documentation content or error
    """
    # Try to find the plugin that contains this element
    plugin_name = _guess_plugin_for_element(element_name)

    urls_to_try = []
    if plugin_name:
        urls_to_try.append(
            f"{GSTREAMER_DOCS_BASE}/{plugin_name}/index.html?gi-language=c#{element_name}"
        )
        urls_to_try.append(
            f"{GSTREAMER_DOCS_BASE}/{plugin_name}/{element_name}.html"
        )

    # Generic search URL
    urls_to_try.append(
        f"{GSTREAMER_DOCS_BASE}/additional/design/{element_name}.html"
    )

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for url in urls_to_try:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    content = response.text

                    # Extract relevant content (basic HTML parsing)
                    doc_content = _extract_doc_content(content, element_name)

                    return {
                        "element": element_name,
                        "url": str(response.url),
                        "content": doc_content,
                        "found": True,
                    }
            except httpx.RequestError:
                continue

    return {
        "element": element_name,
        "found": False,
        "error": f"Documentation not found for '{element_name}'",
        "suggestion": f"Try searching: https://gstreamer.freedesktop.org/documentation/search.html?q={element_name}",
    }


def _guess_plugin_for_element(element_name: str) -> str | None:
    """Guess which plugin an element belongs to based on naming conventions."""
    # Common plugin mappings
    plugin_prefixes = {
        "video": "base",
        "audio": "base",
        "file": "base",
        "app": "base",
        "decode": "base",
        "encode": "base",
        "play": "base",
        "uri": "base",
        "v4l2": "good",
        "pulse": "good",
        "rtsp": "good",
        "rtp": "good",
        "udp": "good",
        "tcp": "good",
        "soup": "good",
        "jpeg": "good",
        "png": "good",
        "flv": "good",
        "matroska": "good",
        "avi": "good",
        "qt": "good",
        "x264": "ugly",
        "x265": "bad",
        "vp8": "good",
        "vp9": "good",
        "opus": "base",
        "vorbis": "base",
        "theora": "base",
        "lame": "ugly",
        "webrtc": "bad",
        "srt": "bad",
        "av1": "bad",
        "va": "bad",
        "nv": "bad",
        "opengl": "base",
        "gl": "base",
    }

    element_lower = element_name.lower()

    for prefix, plugin in plugin_prefixes.items():
        if element_lower.startswith(prefix):
            return f"gst-plugins-{plugin}"

    # Default to base
    return "gst-plugins-base"


def _extract_doc_content(html: str, element_name: str) -> str:
    """Extract documentation content from HTML."""
    # Remove script and style tags
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Try to find the main content
    content_patterns = [
        r'<div class="refsynopsisdiv">.*?</div>',
        r'<div class="refsect\d+">.*?</div>',
        r'<section[^>]*>.*?</section>',
    ]

    extracted = []
    for pattern in content_patterns:
        matches = re.findall(pattern, html, flags=re.DOTALL | re.IGNORECASE)
        for match in matches[:3]:  # Limit to first 3 matches
            # Strip HTML tags
            text = re.sub(r"<[^>]+>", " ", match)
            # Clean up whitespace
            text = re.sub(r"\s+", " ", text).strip()
            if text and len(text) > 50:
                extracted.append(text)

    if extracted:
        return "\n\n".join(extracted[:3])

    # Fallback: just strip all HTML and return a portion
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()

    # Find the part mentioning the element
    element_pos = text.lower().find(element_name.lower())
    if element_pos > 0:
        start = max(0, element_pos - 200)
        end = min(len(text), element_pos + 1000)
        return text[start:end] + "..."

    return text[:1500] + "..." if len(text) > 1500 else text


def get_element_docs_local(element_name: str) -> dict[str, Any]:
    """Get documentation from local GStreamer registry (gst-inspect style).

    Args:
        element_name: Name of the element

    Returns:
        Documentation from the registry
    """
    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import Gst

    if not Gst.is_initialized():
        Gst.init(None)

    factory = Gst.ElementFactory.find(element_name)
    if not factory:
        return {
            "element": element_name,
            "found": False,
            "error": f"Element '{element_name}' not found in registry",
        }

    docs: dict[str, Any] = {
        "element": element_name,
        "found": True,
        "long_name": factory.get_metadata("long-name") or "",
        "description": factory.get_metadata("description") or "",
        "klass": factory.get_metadata("klass") or "",
        "author": factory.get_metadata("author") or "",
        "documentation": factory.get_metadata("doc-element-long-name") or "",
    }

    # Get plugin info
    plugin_name = factory.get_plugin_name()
    if plugin_name:
        registry = Gst.Registry.get()
        plugin = registry.find_plugin(plugin_name)
        if plugin:
            docs["plugin"] = {
                "name": plugin.get_name(),
                "description": plugin.get_description() or "",
                "version": plugin.get_version() or "",
                "license": plugin.get_license() or "",
            }

    return docs
