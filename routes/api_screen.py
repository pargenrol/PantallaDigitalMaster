import markdown as md
from flask import Blueprint, current_app, jsonify, request
from utils.state_files import save_screen_command, load_screen_command

# Flask template registration
bp = Blueprint("api_screen", __name__, url_prefix="/api/screen")


@bp.post("/command")
def api_set_command():
    """
    Handle API request to set a screen command.    
    Retrieves JSON data from the request, extracts the command type and data, and saves the command to a file via the screen command handler.
    
    Returns:
        Response: JSON response indicating successful command execution. Format: {"success": True}
    """
    data = request.get_json(silent=True) or {}
    save_screen_command(
        current_app.config["SCREEN_COMMAND_FILE"],
        data.get("type"),
        data.get("data"),
    )
    return jsonify({"success": True})


@bp.get("/command")
def api_get_command():
    return jsonify(load_screen_command(current_app.config["SCREEN_COMMAND_FILE"], default_type="initiative"))


@bp.post("/show-card")
def api_show_card():
    """
    Handle API request to display an information card on the screen.
    
    Retrieves JSON data from the request body and saves it as a screen command to display an info card. The command is written to the screen command file
    configured in the application settings.
    
    Returns:
        Response: A JSON response with a success status indicating whether the command was processed.
    """
    data = request.get_json(silent=True) or {}
    save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "info_card", data)
    return jsonify({"success": True})


@bp.post("/youtube-control")
def api_youtube_control():
    """
    Handle YouTube control API requests.
    Processes incoming JSON requests to control YouTube playback and saves the control command to a file for screen management.
    
    Expected JSON payload:
        - action (str): The YouTube action to perform (e.g., 'play', 'pause', 'next', 'previous')
    
    Returns:
        Response: JSON response with success status
            - success (bool): True if command was saved successfully
    """
    data = request.get_json(silent=True) or {}
    save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "youtube_control", {"action": data.get("action")})
    return jsonify({"success": True})


@bp.post("/show-image")
def api_show_image():
    """
    Display an image on the screen.
    Expects a JSON request with an 'url' parameter containing the image URL.
    Saves the display command to the screen command file for processing.

    Returns:
        Response: JSON response indicating success status.
    """
    data = request.get_json(silent=True) or {}
    save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "image", {"url": data.get("url")})
    return jsonify({"success": True})


@bp.post("/show-video")
def api_show_video():
    """
    Display a video on the screen.
    Retrieves a JSON payload from the request containing a video URL, saves a command to display the video with autoplay enabled, and returns a success response.
    
    Returns:
        Response: A JSON response with a success flag
    """
    data = request.get_json(silent=True) or {}
    save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "video", {"url": data.get("url"), "autoplay": True})
    return jsonify({"success": True})


@bp.post("/show-youtube")
def api_show_youtube():
    """
    Handle API request to display a YouTube video on the screen.
    Extracts the video_id from the JSON request payload and saves a command to the screen command file to display the YouTube video with autoplay enabled and muted disabled.
    
    Returns:
        Response: JSON object with a success flag indicating the command was saved.
    """
    data = request.get_json(silent=True) or {}
    save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "youtube", {
        "video_id": data.get("video_id"),
        "autoplay": True,
        "muted": False,
    })
    return jsonify({"success": True})


@bp.post("/show-initiative")
def api_show_initiative():
    save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "initiative")
    return jsonify({"success": True})


@bp.post("/clear")
def api_clear_screen():
    save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "clear")
    return jsonify({"success": True})


@bp.post("/blackout")
def api_blackout_screen():
    save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "blackout")
    return jsonify({"success": True})


@bp.post("/toggle-grid")
def api_toggle_grid():
    """
    Toggles the visibility of the grid on the screen.
    This endpoint expects a JSON payload with an optional "show" boolean key to indicate whether the grid should be shown or hidden. It saves the corresponding screen command to the configured command file.

    Returns:
        Response: A JSON response indicating the success of the operation.
    """
    data = request.get_json(silent=True) or {}
    save_screen_command(current_app.config["SCREEN_COMMAND_FILE"], "toggle-grid", {"show": bool(data.get("show", False))})
    return jsonify({"success": True})


@bp.post("/render-markdown-text")
def api_render_markdown_text():
    """
    Converts Markdown text received in a JSON payload to HTML.

    Expects a JSON object in the request body with a "text" field containing Markdown-formatted text. Parses the Markdown text, supporting tables, and returns the resulting HTML in a JSON response.

    Returns:
        Response: A JSON response with keys:
            - "success" (bool): Indicates if the conversion was successful.
            - "html" (str): The resulting HTML string.
    """
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    html = md.markdown(text, extensions=["tables"])
    return jsonify({"success": True, "html": html})
