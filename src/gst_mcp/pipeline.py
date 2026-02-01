"""GStreamer pipeline validation and execution."""

import os
import threading
import uuid
from contextlib import contextmanager
from typing import Any

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib

# Ensure GStreamer is initialized
if not Gst.is_initialized():
    Gst.init(None)


# Global registry of running pipelines
_running_pipelines: dict[str, dict[str, Any]] = {}
_pipelines_lock = threading.Lock()


@contextmanager
def _working_directory(path: str | None):
    """Context manager to temporarily change working directory."""
    if path is None:
        yield
        return

    original = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(original)


def validate_pipeline(pipeline_string: str) -> dict[str, Any]:
    """Validate a GStreamer pipeline string without running it.

    Args:
        pipeline_string: A gst-launch style pipeline string

    Returns:
        Validation result with errors and suggestions
    """
    result: dict[str, Any] = {
        "valid": False,
        "pipeline": pipeline_string,
        "errors": [],
        "warnings": [],
        "suggestions": [],
        "elements": [],
    }

    try:
        pipeline = Gst.parse_launch(pipeline_string)
    except GLib.Error as e:
        error_msg = str(e.message) if hasattr(e, "message") else str(e)
        result["errors"].append(error_msg)

        # Try to provide helpful suggestions
        suggestions = _suggest_fixes(pipeline_string, error_msg)
        result["suggestions"].extend(suggestions)

        return result

    if pipeline is None:
        result["errors"].append("Failed to create pipeline (unknown error)")
        return result

    result["valid"] = True

    # Get pipeline structure
    if isinstance(pipeline, Gst.Pipeline):
        iterator = pipeline.iterate_elements()
        while True:
            ret, elem = iterator.next()
            if ret != Gst.IteratorResult.OK:
                break
            result["elements"].append({
                "name": elem.get_name(),
                "factory": elem.get_factory().get_name() if elem.get_factory() else "unknown",
            })

    # Check for potential issues
    result["warnings"].extend(_check_pipeline_warnings(pipeline))

    # Clean up
    pipeline.set_state(Gst.State.NULL)

    return result


def _suggest_fixes(pipeline_string: str, error_msg: str) -> list[str]:
    """Suggest fixes for common pipeline errors."""
    suggestions = []
    error_lower = error_msg.lower()

    # Element not found
    if "no element" in error_lower or "no such element" in error_lower:
        # Try to extract element name from error
        import re

        match = re.search(r"['\"]([^'\"]+)['\"]", error_msg)
        if match:
            elem_name = match.group(1)
            suggestions.append(f"Element '{elem_name}' not found. Check if the required GStreamer plugin is installed.")
            suggestions.append(f"Run 'gst-inspect-1.0 {elem_name}' to check if the element exists.")

            # Suggest similar elements
            similar = _find_similar_elements(elem_name)
            if similar:
                suggestions.append(f"Did you mean: {', '.join(similar)}?")

    # Link failed
    if "could not link" in error_lower or "link failed" in error_lower:
        suggestions.append("Elements may have incompatible caps. Try adding converter elements:")
        suggestions.append("  For video: videoconvert, videoscale")
        suggestions.append("  For audio: audioconvert, audioresample")

    # Syntax error
    if "syntax error" in error_lower or "unexpected" in error_lower:
        suggestions.append("Check pipeline syntax:")
        suggestions.append("  - Elements are separated by '!'")
        suggestions.append("  - Properties use 'property=value' format")
        suggestions.append("  - Caps use 'media/type,field=value' format")

    return suggestions


def _find_similar_elements(name: str) -> list[str]:
    """Find elements with similar names."""
    registry = Gst.Registry.get()
    factories = registry.get_feature_list(Gst.ElementFactory)

    name_lower = name.lower()
    similar = []

    for factory in factories:
        if not isinstance(factory, Gst.ElementFactory):
            continue
        factory_name = factory.get_name().lower()

        # Check for partial matches
        if name_lower in factory_name or factory_name in name_lower:
            similar.append(factory.get_name())
        # Check for common typos (missing/extra characters)
        elif len(factory_name) == len(name_lower):
            diff = sum(1 for a, b in zip(factory_name, name_lower) if a != b)
            if diff <= 2:
                similar.append(factory.get_name())

        if len(similar) >= 5:
            break

    return similar


def _check_pipeline_warnings(pipeline: Gst.Pipeline) -> list[str]:
    """Check for potential issues in a pipeline."""
    warnings = []

    # This is a basic check - could be expanded
    iterator = pipeline.iterate_elements()
    has_sink = False
    has_source = False

    while True:
        ret, elem = iterator.next()
        if ret != Gst.IteratorResult.OK:
            break

        factory = elem.get_factory()
        if factory:
            klass = factory.get_metadata("klass") or ""
            if "Sink" in klass:
                has_sink = True
            if "Source" in klass:
                has_source = True

    if not has_source:
        warnings.append("Pipeline has no source element")
    if not has_sink:
        warnings.append("Pipeline has no sink element")

    return warnings


def run_pipeline(
    pipeline_string: str,
    timeout_seconds: float | None = None,
    async_mode: bool = False,
    working_directory: str | None = None,
) -> dict[str, Any]:
    """Run a GStreamer pipeline.

    Args:
        pipeline_string: A gst-launch style pipeline string
        timeout_seconds: Optional timeout (for one-shot pipelines)
        async_mode: If True, start pipeline and return immediately with a handle
        working_directory: Directory to run the pipeline in (for relative file paths)

    Returns:
        Execution result or pipeline handle
    """
    # Validate working directory
    if working_directory and not os.path.isdir(working_directory):
        return {
            "success": False,
            "error": f"Working directory does not exist: {working_directory}",
        }

    with _working_directory(working_directory):
        # Validate first
        validation = validate_pipeline(pipeline_string)
        if not validation["valid"]:
            return {
                "success": False,
                "error": "Pipeline validation failed",
                "validation": validation,
            }

        try:
            pipeline = Gst.parse_launch(pipeline_string)
        except GLib.Error as e:
            return {
                "success": False,
                "error": str(e.message) if hasattr(e, "message") else str(e),
            }

        pipeline_id = str(uuid.uuid4())[:8]

        if async_mode:
            # Start pipeline in background
            # Note: For async pipelines, the working_directory is stored so files
            # are written relative to it. The directory change persists for the
            # pipeline's lifetime through the stored path.
            return _start_async_pipeline(pipeline, pipeline_id, pipeline_string, working_directory)
        else:
            # Run pipeline synchronously
            return _run_sync_pipeline(pipeline, pipeline_id, timeout_seconds)


def _start_async_pipeline(
    pipeline: Gst.Pipeline,
    pipeline_id: str,
    pipeline_string: str,
    working_directory: str | None = None,
) -> dict[str, Any]:
    """Start a pipeline in async mode."""
    bus = pipeline.get_bus()
    bus.add_signal_watch()

    pipeline_info = {
        "pipeline": pipeline,
        "pipeline_string": pipeline_string,
        "working_directory": working_directory,
        "state": "starting",
        "messages": [],
        "error": None,
    }

    def on_message(bus: Gst.Bus, message: Gst.Message) -> bool:
        msg_type = message.type

        with _pipelines_lock:
            if pipeline_id not in _running_pipelines:
                return False

            info = _running_pipelines[pipeline_id]

            if msg_type == Gst.MessageType.ERROR:
                err, debug = message.parse_error()
                info["state"] = "error"
                info["error"] = err.message
                info["messages"].append(f"ERROR: {err.message}")
            elif msg_type == Gst.MessageType.EOS:
                info["state"] = "eos"
                info["messages"].append("End of stream")
            elif msg_type == Gst.MessageType.STATE_CHANGED:
                if message.src == pipeline:
                    old, new, pending = message.parse_state_changed()
                    info["state"] = new.value_nick
                    info["messages"].append(f"State: {old.value_nick} -> {new.value_nick}")
            elif msg_type == Gst.MessageType.WARNING:
                warn, debug = message.parse_warning()
                info["messages"].append(f"WARNING: {warn.message}")

        return True

    bus.connect("message", on_message)

    # Start the pipeline
    ret = pipeline.set_state(Gst.State.PLAYING)

    if ret == Gst.StateChangeReturn.FAILURE:
        return {
            "success": False,
            "error": "Failed to start pipeline",
        }

    with _pipelines_lock:
        _running_pipelines[pipeline_id] = pipeline_info

    return {
        "success": True,
        "pipeline_id": pipeline_id,
        "message": "Pipeline started",
        "state": "starting",
    }


def _run_sync_pipeline(
    pipeline: Gst.Pipeline,
    pipeline_id: str,
    timeout_seconds: float | None,
) -> dict[str, Any]:
    """Run a pipeline synchronously with optional timeout."""
    bus = pipeline.get_bus()

    ret = pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        return {"success": False, "error": "Failed to start pipeline"}

    result: dict[str, Any] = {
        "success": True,
        "pipeline_id": pipeline_id,
        "messages": [],
    }

    # Calculate timeout in nanoseconds
    timeout_ns = int(timeout_seconds * Gst.SECOND) if timeout_seconds else Gst.CLOCK_TIME_NONE

    # Wait for EOS or error
    msg = bus.timed_pop_filtered(timeout_ns, Gst.MessageType.ERROR | Gst.MessageType.EOS)

    if msg is None:
        result["success"] = True
        result["status"] = "timeout"
        result["messages"].append(f"Pipeline ran for {timeout_seconds}s (timeout)")
    elif msg.type == Gst.MessageType.ERROR:
        err, debug = msg.parse_error()
        result["success"] = False
        result["error"] = err.message
        result["debug"] = debug
    elif msg.type == Gst.MessageType.EOS:
        result["status"] = "eos"
        result["messages"].append("Pipeline completed (EOS)")

    pipeline.set_state(Gst.State.NULL)

    return result


def get_pipeline_status(pipeline_id: str) -> dict[str, Any]:
    """Get the status of a running pipeline.

    Args:
        pipeline_id: The pipeline ID returned from run_pipeline

    Returns:
        Pipeline status information
    """
    with _pipelines_lock:
        if pipeline_id not in _running_pipelines:
            return {"error": f"Pipeline '{pipeline_id}' not found", "found": False}

        info = _running_pipelines[pipeline_id]
        pipeline = info["pipeline"]

        # Get current state
        ret, state, pending = pipeline.get_state(0)

        return {
            "found": True,
            "pipeline_id": pipeline_id,
            "state": state.value_nick if ret == Gst.StateChangeReturn.SUCCESS else info["state"],
            "pending_state": pending.value_nick if pending != Gst.State.VOID_PENDING else None,
            "error": info.get("error"),
            "recent_messages": info["messages"][-10:],  # Last 10 messages
        }


def stop_pipeline(pipeline_id: str) -> dict[str, Any]:
    """Stop a running pipeline.

    Args:
        pipeline_id: The pipeline ID returned from run_pipeline

    Returns:
        Stop result
    """
    with _pipelines_lock:
        if pipeline_id not in _running_pipelines:
            return {"error": f"Pipeline '{pipeline_id}' not found", "success": False}

        info = _running_pipelines[pipeline_id]
        pipeline = info["pipeline"]

        # Stop the pipeline
        pipeline.set_state(Gst.State.NULL)

        # Remove from registry
        del _running_pipelines[pipeline_id]

    return {
        "success": True,
        "pipeline_id": pipeline_id,
        "message": "Pipeline stopped",
    }


def list_running_pipelines() -> list[dict[str, Any]]:
    """List all running pipelines.

    Returns:
        List of running pipeline summaries
    """
    with _pipelines_lock:
        result = []
        for pid, info in _running_pipelines.items():
            result.append({
                "pipeline_id": pid,
                "state": info["state"],
                "pipeline_string": info["pipeline_string"][:100] + "..."
                if len(info["pipeline_string"]) > 100
                else info["pipeline_string"],
            })
        return result


def get_pipeline_graph(pipeline_string: str) -> dict[str, Any]:
    """Generate a DOT graph representation of a pipeline.

    Args:
        pipeline_string: A gst-launch style pipeline string

    Returns:
        DOT graph string or error
    """
    try:
        pipeline = Gst.parse_launch(pipeline_string)
    except GLib.Error as e:
        return {"error": str(e.message) if hasattr(e, "message") else str(e)}

    if pipeline is None:
        return {"error": "Failed to create pipeline"}

    # Set to PAUSED to negotiate caps
    pipeline.set_state(Gst.State.PAUSED)

    # Generate DOT graph
    dot = Gst.debug_bin_to_dot_data(pipeline, Gst.DebugGraphDetails.ALL)

    pipeline.set_state(Gst.State.NULL)

    return {
        "dot": dot,
        "message": "Use 'dot -Tpng graph.dot -o graph.png' to render",
    }
