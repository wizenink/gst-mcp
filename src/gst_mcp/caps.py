"""GStreamer caps parsing and compatibility utilities."""

from typing import Any

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst

# Ensure GStreamer is initialized
if not Gst.is_initialized():
    Gst.init(None)


def parse_caps(caps_string: str) -> dict[str, Any]:
    """Parse a GStreamer caps string and return structured information.

    Args:
        caps_string: A GStreamer caps string (e.g., "video/x-raw,format=I420,width=1920")

    Returns:
        Structured caps information
    """
    try:
        caps = Gst.Caps.from_string(caps_string)
    except Exception as e:
        return {"error": f"Failed to parse caps: {e}", "valid": False}

    if caps is None:
        return {"error": "Invalid caps string", "valid": False}

    result: dict[str, Any] = {
        "valid": True,
        "is_any": caps.is_any(),
        "is_empty": caps.is_empty(),
        "is_fixed": caps.is_fixed(),
        "structures": [],
    }

    for i in range(caps.get_size()):
        structure = caps.get_structure(i)
        struct_info: dict[str, Any] = {
            "name": structure.get_name(),
            "fields": {},
        }

        for j in range(structure.n_fields()):
            field_name = structure.nth_field_name(j)
            value = structure.get_value(field_name)
            struct_info["fields"][field_name] = _gvalue_to_python(value)

        result["structures"].append(struct_info)

    return result


def _gvalue_to_python(value: Any) -> Any:
    """Convert a GValue to a Python representation."""
    if value is None:
        return None

    # Handle GStreamer specific types
    if isinstance(value, Gst.IntRange):
        return {"type": "int_range", "min": value.range.start, "max": value.range.stop}
    elif isinstance(value, Gst.FractionRange):
        return {
            "type": "fraction_range",
            "min": f"{value.start.num}/{value.start.denom}",
            "max": f"{value.stop.num}/{value.stop.denom}",
        }
    elif isinstance(value, Gst.Fraction):
        return {"type": "fraction", "value": f"{value.num}/{value.denom}"}
    elif isinstance(value, Gst.ValueList):
        return {"type": "list", "values": [_gvalue_to_python(v) for v in value]}
    elif isinstance(value, Gst.ValueArray):
        return {"type": "array", "values": [_gvalue_to_python(v) for v in value]}
    elif hasattr(value, "value_nick"):
        return {"type": "enum", "value": value.value_nick}
    else:
        return str(value)


def check_caps_compatible(caps1_string: str, caps2_string: str) -> dict[str, Any]:
    """Check if two caps can intersect (are compatible).

    Args:
        caps1_string: First caps string
        caps2_string: Second caps string

    Returns:
        Compatibility information
    """
    try:
        caps1 = Gst.Caps.from_string(caps1_string)
        caps2 = Gst.Caps.from_string(caps2_string)
    except Exception as e:
        return {"error": f"Failed to parse caps: {e}", "compatible": False}

    if caps1 is None or caps2 is None:
        return {"error": "Invalid caps string", "compatible": False}

    compatible = caps1.can_intersect(caps2)
    intersection = caps1.intersect(caps2)

    result: dict[str, Any] = {
        "compatible": compatible,
        "caps1_any": caps1.is_any(),
        "caps2_any": caps2.is_any(),
    }

    if compatible and not intersection.is_empty():
        result["intersection"] = intersection.to_string()

    return result


def check_elements_can_link(
    src_element: str,
    sink_element: str,
    src_pad_name: str | None = None,
    sink_pad_name: str | None = None,
) -> dict[str, Any]:
    """Check if two elements can link based on their pad caps.

    Args:
        src_element: Name of the source element
        sink_element: Name of the sink element
        src_pad_name: Optional specific src pad name
        sink_pad_name: Optional specific sink pad name

    Returns:
        Linkability information
    """
    src_factory = Gst.ElementFactory.find(src_element)
    sink_factory = Gst.ElementFactory.find(sink_element)

    if not src_factory:
        return {"error": f"Element '{src_element}' not found", "can_link": False}
    if not sink_factory:
        return {"error": f"Element '{sink_element}' not found", "can_link": False}

    # Get src pads from source element
    src_templates = [
        t for t in src_factory.get_static_pad_templates() if t.direction == Gst.PadDirection.SRC
    ]
    # Get sink pads from sink element
    sink_templates = [
        t for t in sink_factory.get_static_pad_templates() if t.direction == Gst.PadDirection.SINK
    ]

    if not src_templates:
        return {"error": f"Element '{src_element}' has no src pads", "can_link": False}
    if not sink_templates:
        return {"error": f"Element '{sink_element}' has no sink pads", "can_link": False}

    # Filter by pad name if specified
    if src_pad_name:
        src_templates = [t for t in src_templates if t.name_template == src_pad_name]
    if sink_pad_name:
        sink_templates = [t for t in sink_templates if t.name_template == sink_pad_name]

    # Check all combinations
    compatible_pairs = []
    for src_tmpl in src_templates:
        src_caps = Gst.Caps.from_string(src_tmpl.static_caps.string) if src_tmpl.static_caps else Gst.Caps.new_any()

        for sink_tmpl in sink_templates:
            sink_caps = (
                Gst.Caps.from_string(sink_tmpl.static_caps.string)
                if sink_tmpl.static_caps
                else Gst.Caps.new_any()
            )

            if src_caps and sink_caps and src_caps.can_intersect(sink_caps):
                intersection = src_caps.intersect(sink_caps)
                compatible_pairs.append({
                    "src_pad": src_tmpl.name_template,
                    "sink_pad": sink_tmpl.name_template,
                    "src_caps": src_tmpl.static_caps.string if src_tmpl.static_caps else "ANY",
                    "sink_caps": sink_tmpl.static_caps.string if sink_tmpl.static_caps else "ANY",
                    "intersection": intersection.to_string() if intersection and not intersection.is_empty() else None,
                })

    return {
        "can_link": len(compatible_pairs) > 0,
        "src_element": src_element,
        "sink_element": sink_element,
        "compatible_pads": compatible_pairs,
    }


# Common converter elements for different media types
CONVERTERS = {
    "video/x-raw": ["videoconvert", "videoscale", "videorate"],
    "audio/x-raw": ["audioconvert", "audioresample", "audiorate"],
    "video": ["decodebin", "videoconvert", "videoscale"],
    "audio": ["decodebin", "audioconvert", "audioresample"],
    "text": ["textoverlay"],
}


def suggest_converter(
    src_element: str,
    sink_element: str,
) -> dict[str, Any]:
    """Suggest converter elements to link incompatible elements.

    Args:
        src_element: Name of the source element
        sink_element: Name of the sink element

    Returns:
        Suggested converters and pipeline snippets
    """
    # First check if they can link directly
    link_check = check_elements_can_link(src_element, sink_element)
    if link_check.get("can_link"):
        return {
            "direct_link_possible": True,
            "suggestions": [],
            "message": f"'{src_element}' and '{sink_element}' can link directly",
        }

    src_factory = Gst.ElementFactory.find(src_element)
    sink_factory = Gst.ElementFactory.find(sink_element)

    if not src_factory or not sink_factory:
        return {
            "direct_link_possible": False,
            "suggestions": [],
            "error": "One or both elements not found",
        }

    # Analyze src output caps and sink input caps
    src_caps_info = _analyze_element_caps(src_factory, Gst.PadDirection.SRC)
    sink_caps_info = _analyze_element_caps(sink_factory, Gst.PadDirection.SINK)

    suggestions = []

    # Video raw to video raw (different formats)
    if "video/x-raw" in src_caps_info["media_types"] and "video/x-raw" in sink_caps_info["media_types"]:
        suggestions.append({
            "converters": ["videoconvert"],
            "pipeline": f"{src_element} ! videoconvert ! {sink_element}",
            "reason": "Convert between video formats",
        })
        suggestions.append({
            "converters": ["videoconvert", "videoscale"],
            "pipeline": f"{src_element} ! videoconvert ! videoscale ! {sink_element}",
            "reason": "Convert format and scale video",
        })

    # Audio raw to audio raw
    if "audio/x-raw" in src_caps_info["media_types"] and "audio/x-raw" in sink_caps_info["media_types"]:
        suggestions.append({
            "converters": ["audioconvert"],
            "pipeline": f"{src_element} ! audioconvert ! {sink_element}",
            "reason": "Convert between audio formats",
        })
        suggestions.append({
            "converters": ["audioconvert", "audioresample"],
            "pipeline": f"{src_element} ! audioconvert ! audioresample ! {sink_element}",
            "reason": "Convert format and resample audio",
        })

    # Encoded to raw (needs decoder)
    if src_caps_info["is_encoded"] and not sink_caps_info["is_encoded"]:
        suggestions.append({
            "converters": ["decodebin"],
            "pipeline": f"{src_element} ! decodebin ! {sink_element}",
            "reason": "Decode encoded media",
        })

    # Raw to encoded (needs encoder)
    if not src_caps_info["is_encoded"] and sink_caps_info["is_encoded"]:
        if "video" in src_caps_info["media_types"] or "video/x-raw" in src_caps_info["media_types"]:
            suggestions.append({
                "converters": ["videoconvert", "x264enc"],
                "pipeline": f"{src_element} ! videoconvert ! x264enc ! {sink_element}",
                "reason": "Encode video to H.264",
            })
        if "audio" in src_caps_info["media_types"] or "audio/x-raw" in src_caps_info["media_types"]:
            suggestions.append({
                "converters": ["audioconvert", "lamemp3enc"],
                "pipeline": f"{src_element} ! audioconvert ! lamemp3enc ! {sink_element}",
                "reason": "Encode audio to MP3",
            })

    # Generic fallback with decodebin
    if not suggestions:
        suggestions.append({
            "converters": ["decodebin", "videoconvert", "videoscale"],
            "pipeline": f"{src_element} ! decodebin ! videoconvert ! videoscale ! {sink_element}",
            "reason": "Generic decode and convert (video)",
        })
        suggestions.append({
            "converters": ["decodebin", "audioconvert", "audioresample"],
            "pipeline": f"{src_element} ! decodebin ! audioconvert ! audioresample ! {sink_element}",
            "reason": "Generic decode and convert (audio)",
        })

    return {
        "direct_link_possible": False,
        "src_output_types": src_caps_info["media_types"],
        "sink_input_types": sink_caps_info["media_types"],
        "suggestions": suggestions,
    }


def _analyze_element_caps(factory: Gst.ElementFactory, direction: Gst.PadDirection) -> dict[str, Any]:
    """Analyze the caps of an element's pads in a given direction."""
    templates = [t for t in factory.get_static_pad_templates() if t.direction == direction]

    media_types: set[str] = set()
    is_encoded = False

    for template in templates:
        if not template.static_caps:
            continue

        caps_str = template.static_caps.string
        caps = Gst.Caps.from_string(caps_str)

        if caps:
            for i in range(caps.get_size()):
                struct = caps.get_structure(i)
                name = struct.get_name()
                media_types.add(name)

                # Check if it's an encoded format
                if name.startswith("video/x-") and name != "video/x-raw":
                    is_encoded = True
                elif name.startswith("audio/x-") and name != "audio/x-raw":
                    is_encoded = True
                elif name.startswith("audio/mpeg"):
                    is_encoded = True

    return {
        "media_types": list(media_types),
        "is_encoded": is_encoded,
    }
