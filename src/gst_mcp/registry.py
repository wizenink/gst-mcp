"""GStreamer registry introspection functions."""

from typing import Any

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst

# Ensure GStreamer is initialized
if not Gst.is_initialized():
    Gst.init(None)


def _get_element_category(factory: Gst.ElementFactory) -> str:
    """Determine the category of an element based on its klass."""
    klass = factory.get_metadata("klass") or ""
    klass_lower = klass.lower()

    if "source" in klass_lower or "src" in klass_lower:
        return "source"
    elif "sink" in klass_lower:
        return "sink"
    elif "decoder" in klass_lower:
        return "decoder"
    elif "encoder" in klass_lower:
        return "encoder"
    elif "muxer" in klass_lower or "mux" in klass_lower:
        return "muxer"
    elif "demuxer" in klass_lower or "demux" in klass_lower:
        return "demuxer"
    elif "filter" in klass_lower or "effect" in klass_lower:
        return "filter"
    elif "parser" in klass_lower:
        return "parser"
    elif "payloader" in klass_lower:
        return "payloader"
    elif "depayloader" in klass_lower:
        return "depayloader"
    elif "converter" in klass_lower:
        return "converter"
    else:
        return "other"


def _get_rank_name(rank: int) -> str:
    """Convert rank integer to human-readable name."""
    if rank == 0:
        return "none"
    elif rank == 64:
        return "marginal"
    elif rank == 128:
        return "secondary"
    elif rank == 256:
        return "primary"
    else:
        return str(rank)


def list_elements(category: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """List available GStreamer elements, optionally filtered by category.

    Args:
        category: Filter by category (source, sink, decoder, encoder, muxer, demuxer, filter, parser, other)
        limit: Maximum number of elements to return

    Returns:
        List of element info dictionaries
    """
    registry = Gst.Registry.get()
    factories = registry.get_feature_list(Gst.ElementFactory)

    elements = []
    for factory in factories:
        if not isinstance(factory, Gst.ElementFactory):
            continue

        elem_category = _get_element_category(factory)
        if category and elem_category != category.lower():
            continue

        elements.append({
            "name": factory.get_name(),
            "description": factory.get_metadata("description") or "",
            "category": elem_category,
            "klass": factory.get_metadata("klass") or "",
            "rank": _get_rank_name(factory.get_rank()),
        })

        if len(elements) >= limit:
            break

    return sorted(elements, key=lambda x: x["name"])


def get_element_info(element_name: str) -> dict[str, Any] | None:
    """Get detailed information about a GStreamer element.

    Args:
        element_name: Name of the element (e.g., "videotestsrc", "x264enc")

    Returns:
        Detailed element information or None if not found
    """
    factory = Gst.ElementFactory.find(element_name)
    if not factory:
        return None

    # Get basic info
    info: dict[str, Any] = {
        "name": factory.get_name(),
        "description": factory.get_metadata("description") or "",
        "long_name": factory.get_metadata("long-name") or "",
        "klass": factory.get_metadata("klass") or "",
        "author": factory.get_metadata("author") or "",
        "category": _get_element_category(factory),
        "rank": _get_rank_name(factory.get_rank()),
        "plugin": factory.get_plugin_name(),
    }

    # Get pad templates
    info["pad_templates"] = []
    for template in factory.get_static_pad_templates():
        pad_info = {
            "name": template.name_template,
            "direction": "src" if template.direction == Gst.PadDirection.SRC else "sink",
            "presence": template.presence.value_nick,
            "caps": template.static_caps.string if template.static_caps else "ANY",
        }
        info["pad_templates"].append(pad_info)

    # Get properties by creating a temporary element
    try:
        element = factory.create(None)
        if element:
            info["properties"] = _get_element_properties(element)
            info["signals"] = _get_element_signals(element)
    except Exception:
        info["properties"] = []
        info["signals"] = []

    return info


def _get_element_properties(element: Gst.Element) -> list[dict[str, Any]]:
    """Get properties of an element."""
    properties = []

    for prop in element.__class__.list_properties():
        if prop.name in ("name", "parent"):  # Skip common inherited props
            continue

        prop_info: dict[str, Any] = {
            "name": prop.name,
            "nick": prop.nick,
            "blurb": prop.blurb,
            "type": prop.value_type.name,
            "flags": [],
        }

        # Get flags
        if prop.flags & 1:  # G_PARAM_READABLE
            prop_info["flags"].append("readable")
        if prop.flags & 2:  # G_PARAM_WRITABLE
            prop_info["flags"].append("writable")

        # Get default/range for numeric types
        if hasattr(prop, "minimum") and hasattr(prop, "maximum"):
            prop_info["minimum"] = prop.minimum
            prop_info["maximum"] = prop.maximum
        if hasattr(prop, "default_value"):
            try:
                prop_info["default"] = prop.default_value
            except Exception:
                pass

        properties.append(prop_info)

    return properties


def _get_element_signals(element: Gst.Element) -> list[dict[str, Any]]:
    """Get signals of an element."""
    signals = []

    # Get signal IDs for the element type
    try:
        from gi.repository import GObject

        type_class = type(element)
        signal_ids = GObject.signal_list_ids(type_class)

        for signal_id in signal_ids:
            signal_query = GObject.signal_query(signal_id)
            if signal_query:
                signals.append({
                    "name": signal_query.signal_name,
                    "return_type": signal_query.return_type.name if signal_query.return_type else "void",
                    "n_params": signal_query.n_params,
                })
    except Exception:
        pass

    return signals


def list_plugins() -> list[dict[str, Any]]:
    """List all installed GStreamer plugins.

    Returns:
        List of plugin info dictionaries
    """
    registry = Gst.Registry.get()
    plugins = registry.get_plugin_list()

    result = []
    for plugin in plugins:
        result.append({
            "name": plugin.get_name(),
            "description": plugin.get_description() or "",
            "version": plugin.get_version() or "",
            "license": plugin.get_license() or "",
            "source": plugin.get_source() or "",
            "filename": plugin.get_filename() or "",
        })

    return sorted(result, key=lambda x: x["name"])


def get_plugin_info(plugin_name: str) -> dict[str, Any] | None:
    """Get detailed information about a GStreamer plugin.

    Args:
        plugin_name: Name of the plugin

    Returns:
        Plugin information with its elements, or None if not found
    """
    registry = Gst.Registry.get()
    plugin = registry.find_plugin(plugin_name)

    if not plugin:
        return None

    info: dict[str, Any] = {
        "name": plugin.get_name(),
        "description": plugin.get_description() or "",
        "version": plugin.get_version() or "",
        "license": plugin.get_license() or "",
        "source": plugin.get_source() or "",
        "filename": plugin.get_filename() or "",
    }

    # Get elements provided by this plugin
    features = registry.get_feature_list_by_plugin(plugin_name)
    elements = []
    for feature in features:
        if isinstance(feature, Gst.ElementFactory):
            elements.append({
                "name": feature.get_name(),
                "description": feature.get_metadata("description") or "",
                "klass": feature.get_metadata("klass") or "",
            })

    info["elements"] = sorted(elements, key=lambda x: x["name"])

    return info


def search_elements(
    query: str,
    search_in: list[str] | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Search for elements by name, description, or caps.

    Args:
        query: Search query string
        search_in: Fields to search in (name, description, caps). Defaults to all.
        limit: Maximum results to return

    Returns:
        List of matching element info dictionaries
    """
    if search_in is None:
        search_in = ["name", "description", "caps"]

    query_lower = query.lower()
    registry = Gst.Registry.get()
    factories = registry.get_feature_list(Gst.ElementFactory)

    results = []
    for factory in factories:
        if not isinstance(factory, Gst.ElementFactory):
            continue

        matched = False

        if "name" in search_in and query_lower in factory.get_name().lower():
            matched = True
        elif "description" in search_in:
            desc = factory.get_metadata("description") or ""
            if query_lower in desc.lower():
                matched = True
        elif "caps" in search_in:
            for template in factory.get_static_pad_templates():
                caps_str = template.static_caps.string if template.static_caps else ""
                if query_lower in caps_str.lower():
                    matched = True
                    break

        if matched:
            results.append({
                "name": factory.get_name(),
                "description": factory.get_metadata("description") or "",
                "category": _get_element_category(factory),
                "klass": factory.get_metadata("klass") or "",
            })

            if len(results) >= limit:
                break

    return results
