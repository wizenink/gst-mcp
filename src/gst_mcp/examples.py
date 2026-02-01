"""GStreamer pipeline examples organized by category."""

from typing import Any


EXAMPLES: dict[str, list[dict[str, Any]]] = {
    "playback": [
        {
            "name": "Play video file",
            "description": "Play a video file with automatic codec detection",
            "pipeline": "filesrc location=/path/to/video.mp4 ! decodebin ! autovideosink",
            "notes": "Replace /path/to/video.mp4 with actual file path",
        },
        {
            "name": "Play audio file",
            "description": "Play an audio file with automatic codec detection",
            "pipeline": "filesrc location=/path/to/audio.mp3 ! decodebin ! audioconvert ! audioresample ! autoaudiosink",
            "notes": "Works with MP3, FLAC, WAV, OGG, and other formats",
        },
        {
            "name": "Play video with audio",
            "description": "Play video file with both video and audio output",
            "pipeline": "playbin uri=file:///path/to/video.mp4",
            "notes": "playbin is a high-level element that handles everything",
        },
        {
            "name": "Play from URL",
            "description": "Stream and play media from HTTP URL",
            "pipeline": "playbin uri=https://example.com/video.mp4",
            "notes": "Requires souphttpsrc or curlhttpsrc plugin",
        },
    ],
    "transcoding": [
        {
            "name": "Convert to H.264 MP4",
            "description": "Transcode video to H.264 in MP4 container",
            "pipeline": "filesrc location=input.mkv ! decodebin name=dec ! queue ! videoconvert ! x264enc ! h264parse ! mp4mux name=mux ! filesink location=output.mp4 dec. ! queue ! audioconvert ! audioresample ! avenc_aac ! mux.",
            "notes": "Requires gst-plugins-ugly for x264enc and gst-libav for avenc_aac",
        },
        {
            "name": "Convert to WebM (VP9)",
            "description": "Transcode video to VP9 in WebM container",
            "pipeline": "filesrc location=input.mp4 ! decodebin name=dec ! queue ! videoconvert ! vp9enc ! webmmux name=mux ! filesink location=output.webm dec. ! queue ! audioconvert ! audioresample ! opusenc ! mux.",
            "notes": "Good for web delivery",
        },
        {
            "name": "Extract audio to MP3",
            "description": "Extract audio track and convert to MP3",
            "pipeline": "filesrc location=video.mp4 ! decodebin ! audioconvert ! audioresample ! lamemp3enc ! filesink location=audio.mp3",
            "notes": "Requires gst-plugins-ugly for lamemp3enc",
        },
        {
            "name": "Resize video",
            "description": "Resize video to specific resolution",
            "pipeline": "filesrc location=input.mp4 ! decodebin ! videoconvert ! videoscale ! video/x-raw,width=1280,height=720 ! x264enc ! mp4mux ! filesink location=output.mp4",
            "notes": "Change width and height caps as needed",
        },
        {
            "name": "Convert framerate",
            "description": "Change video framerate",
            "pipeline": "filesrc location=input.mp4 ! decodebin ! videoconvert ! videorate ! video/x-raw,framerate=30/1 ! x264enc ! mp4mux ! filesink location=output.mp4",
            "notes": "Use videorate element to change framerate",
        },
    ],
    "streaming": [
        {
            "name": "RTMP streaming",
            "description": "Stream to RTMP server (Twitch, YouTube, etc.)",
            "pipeline": "videotestsrc ! videoconvert ! x264enc tune=zerolatency ! flvmux streamable=true name=mux ! rtmpsink location='rtmp://server/app/stream_key' audiotestsrc ! audioconvert ! voaacenc ! mux.",
            "notes": "Replace with your actual RTMP URL and stream key",
        },
        {
            "name": "RTP video streaming",
            "description": "Stream video over RTP/UDP",
            "pipeline": "videotestsrc ! videoconvert ! x264enc tune=zerolatency ! rtph264pay ! udpsink host=127.0.0.1 port=5000",
            "notes": "Receive with: gst-launch-1.0 udpsrc port=5000 ! application/x-rtp ! rtph264depay ! decodebin ! autovideosink",
        },
        {
            "name": "HLS output",
            "description": "Generate HLS playlist for adaptive streaming",
            "pipeline": "videotestsrc ! videoconvert ! x264enc ! mpegtsmux ! hlssink max-files=5 target-duration=2 location=segment%05d.ts playlist-location=playlist.m3u8",
            "notes": "Creates HLS segments and playlist file",
        },
        {
            "name": "RTSP server (test)",
            "description": "Simple test pattern for RTSP (use with gst-rtsp-server)",
            "pipeline": "videotestsrc ! videoconvert ! x264enc tune=zerolatency ! rtph264pay name=pay0 pt=96",
            "notes": "This is the pipeline for gst-rtsp-server, not standalone gst-launch",
        },
    ],
    "capture": [
        {
            "name": "Webcam capture (Linux)",
            "description": "Capture from webcam using V4L2",
            "pipeline": "v4l2src device=/dev/video0 ! videoconvert ! autovideosink",
            "notes": "Change device path as needed",
        },
        {
            "name": "Screen capture (X11)",
            "description": "Capture screen on X11",
            "pipeline": "ximagesrc ! videoconvert ! autovideosink",
            "notes": "Use startx and endx/endy to capture specific region",
        },
        {
            "name": "Screen capture (PipeWire)",
            "description": "Capture screen on Wayland via PipeWire",
            "pipeline": "pipewiresrc ! videoconvert ! autovideosink",
            "notes": "Requires PipeWire and appropriate permissions",
        },
        {
            "name": "Microphone capture",
            "description": "Capture audio from microphone (PulseAudio)",
            "pipeline": "pulsesrc ! audioconvert ! audioresample ! autoaudiosink",
            "notes": "Use pulsesrc device property to select specific source",
        },
        {
            "name": "Webcam to file",
            "description": "Record webcam to MP4 file",
            "pipeline": "v4l2src device=/dev/video0 ! videoconvert ! x264enc tune=zerolatency ! mp4mux ! filesink location=webcam.mp4",
            "notes": "Press Ctrl+C to stop recording",
        },
    ],
    "effects": [
        {
            "name": "Video brightness/contrast",
            "description": "Adjust video brightness and contrast",
            "pipeline": "videotestsrc ! videoconvert ! videobalance brightness=0.5 contrast=1.5 ! autovideosink",
            "notes": "brightness: -1.0 to 1.0, contrast: 0.0 to 2.0",
        },
        {
            "name": "Video flip/rotate",
            "description": "Flip or rotate video",
            "pipeline": "videotestsrc ! videoconvert ! videoflip method=rotate-180 ! autovideosink",
            "notes": "Methods: rotate-90, rotate-180, rotate-270, horizontal-flip, vertical-flip",
        },
        {
            "name": "Text overlay",
            "description": "Add text overlay to video",
            "pipeline": "videotestsrc ! videoconvert ! textoverlay text='Hello World' font-desc='Sans 48' ! autovideosink",
            "notes": "Use valignment and halignment for positioning",
        },
        {
            "name": "Picture-in-picture",
            "description": "Composite two videos (PiP effect)",
            "pipeline": "videotestsrc pattern=0 ! videoconvert ! videoscale ! video/x-raw,width=640,height=480 ! compositor name=comp sink_0::xpos=0 sink_0::ypos=0 sink_1::xpos=400 sink_1::ypos=300 ! autovideosink videotestsrc pattern=18 ! videoconvert ! videoscale ! video/x-raw,width=200,height=150 ! comp.",
            "notes": "Uses compositor element for video mixing",
        },
        {
            "name": "Audio echo effect",
            "description": "Add echo/delay to audio",
            "pipeline": "audiotestsrc ! audioconvert ! audioecho delay=500000000 intensity=0.5 feedback=0.4 ! autoaudiosink",
            "notes": "delay is in nanoseconds (500000000 = 0.5 seconds)",
        },
        {
            "name": "Volume control",
            "description": "Adjust audio volume",
            "pipeline": "audiotestsrc ! audioconvert ! volume volume=0.5 ! autoaudiosink",
            "notes": "volume: 0.0 = mute, 1.0 = 100%, >1.0 = amplify",
        },
    ],
    "testing": [
        {
            "name": "Video test pattern",
            "description": "Display test video pattern",
            "pipeline": "videotestsrc ! autovideosink",
            "notes": "Use pattern property: 0=smpte, 1=snow, 18=ball, etc.",
        },
        {
            "name": "Audio test tone",
            "description": "Play test audio tone",
            "pipeline": "audiotestsrc ! autoaudiosink",
            "notes": "Use wave property: 0=sine, 1=square, 2=saw, etc.",
        },
        {
            "name": "Null sink (benchmark)",
            "description": "Benchmark decoding speed with null sink",
            "pipeline": "filesrc location=video.mp4 ! decodebin ! fakesink sync=false",
            "notes": "Measures decode speed without display overhead",
        },
        {
            "name": "Caps debug",
            "description": "Show negotiated caps between elements",
            "pipeline": "videotestsrc ! identity silent=false ! videoconvert ! autovideosink",
            "notes": "identity element shows buffer info, use GST_DEBUG=2 for more",
        },
    ],
    "analysis": [
        {
            "name": "Get media info",
            "description": "Discover media file information",
            "pipeline": "filesrc location=video.mp4 ! decodebin ! fakesink",
            "notes": "Use discoverer API instead for better results",
        },
        {
            "name": "Generate waveform",
            "description": "Visualize audio waveform",
            "pipeline": "filesrc location=audio.mp3 ! decodebin ! audioconvert ! wavescope ! videoconvert ! autovideosink",
            "notes": "Other visualizers: spectrascope, synaescope, spacescope",
        },
        {
            "name": "Audio level meter",
            "description": "Show audio levels",
            "pipeline": "audiotestsrc ! audioconvert ! level post-messages=true ! fakesink",
            "notes": "Level messages are posted to bus, use GST_DEBUG=level:5",
        },
    ],
}


def get_examples(category: str | None = None) -> dict[str, Any]:
    """Get pipeline examples, optionally filtered by category.

    Args:
        category: Category to filter by (playback, transcoding, streaming, capture, effects, testing, analysis)

    Returns:
        Examples organized by category
    """
    if category:
        category_lower = category.lower()
        if category_lower in EXAMPLES:
            return {
                "category": category_lower,
                "examples": EXAMPLES[category_lower],
            }
        else:
            return {
                "error": f"Unknown category: {category}",
                "available_categories": list(EXAMPLES.keys()),
            }

    return {
        "categories": list(EXAMPLES.keys()),
        "examples": EXAMPLES,
    }


def list_example_categories() -> list[str]:
    """List available example categories.

    Returns:
        List of category names
    """
    return list(EXAMPLES.keys())
