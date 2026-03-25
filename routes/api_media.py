import os
from flask import Blueprint, current_app, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

# Flask template registration
bp = Blueprint("api_media", __name__)


@bp.post("/api/media/upload")
def api_upload_media():
    """
    Handle media file uploads and organize them by type.
    Processes incoming file uploads via multipart/form-data, validates the file, determines its type (audio, video, or image), and saves it to the appropriate directory. 
    The media type can be explicitly specified via the 'type' query parameter or automatically detected based on file extension.
    Query Parameters:
        type (str, optional): Media type classification ("audio", "video", or "image"). If not provided or set to "auto", type is detected from file extension.
                              Defaults to "auto".
    Request Files:
        file (FileStorage): The media file to upload. Required.
    Returns:
        tuple: A tuple containing:
            - dict: JSON response with keys:
                - "success" (bool): True if upload succeeded, False otherwise
                - "url" (str): Relative URL path to the uploaded file (only on success)
                - "filename" (str): The sanitized filename (only on success)
            - int: HTTP status code (200 on success, 400 on error)
    File Organization:
        - Audio files (.mp3, .wav, .ogg) → uploads/audio/
        - Video files (.mp4, .webm, .mov) → uploads/videos/
        - All other files → uploads/images/
    """
    if "file" in request.files:
        file = request.files["file"]

        if file.filename != "":
            media_type = request.args.get("type", "auto")
            filename = secure_filename(file.filename)
            extension = filename.lower()

            if media_type == "audio" or extension.endswith((".mp3", ".wav", ".ogg")):
                folder_name = "audio"
            elif extension.endswith((".mp4", ".webm", ".mov")):
                folder_name = "videos"
            else:
                folder_name = "images"

            target_folder = os.path.join(current_app.config["UPLOAD_DIR"], folder_name)
            os.makedirs(target_folder, exist_ok=True)
            file.save(os.path.join(target_folder, filename))

            return jsonify({
                "success": True,
                "url": f"/static/uploads/{folder_name}/{filename}",
                "filename": filename
            })
        else:
            return jsonify({"success": False}), 400
    else:
        return jsonify({"success": False}), 400


@bp.get("/static/uploads/<path:filename>")
def serve_uploads(filename):
    return send_from_directory(current_app.config["UPLOAD_DIR"], filename)


@bp.get("/api/audio/list")
def list_audios():
    """
    Retrieve a list of audio files from the application's audio directory.
    This function scans the audio directory (located in UPLOAD_DIR/audio) for files with audio extensions (.mp3, .wav, .ogg) and returns them as a JSON response.

    The audio directory is created if it does not exist. If any error occurs during the file listing process, an empty list is returned.

    Returns:
        Response: A Flask JSON response containing a list of audio filenames (strings)
                  with supported audio extensions, or an empty list if an error occurs.
    """
    audio_dir = os.path.join(current_app.config["UPLOAD_DIR"], "audio")
    os.makedirs(audio_dir, exist_ok=True)
    try:
        files = [f for f in os.listdir(audio_dir) if f.lower().endswith((".mp3", ".wav", ".ogg"))]
        return jsonify(files)
    except Exception:
        return jsonify([])
