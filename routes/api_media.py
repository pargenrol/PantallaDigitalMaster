import json
import os
from flask import Blueprint, current_app, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

AUDIO_CATEGORIES = ["combate", "exploración", "tensión", "ciudad", "mazmorra", "descanso", "sting", "ambiente"]


def _metadata_path(app):
    return os.path.join(app.config["UPLOAD_DIR"], "audio", "metadata.json")


def _playlists_path(app):
    return os.path.join(app.config["UPLOAD_DIR"], "audio", "playlists.json")


def _load_playlists(app):
    path = _playlists_path(app)
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_playlists(app, playlists):
    path = _playlists_path(app)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(playlists, f, ensure_ascii=False, indent=2)


def _load_metadata(app):
    path = _metadata_path(app)
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_metadata(app, metadata):
    path = _metadata_path(app)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

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
            elif media_type == "html" or extension.endswith((".html", ".htm")):
                folder_name = "html"
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
    audio_dir = os.path.join(current_app.config["UPLOAD_DIR"], "audio")
    os.makedirs(audio_dir, exist_ok=True)
    try:
        metadata = _load_metadata(current_app._get_current_object())
        files = sorted(f for f in os.listdir(audio_dir) if f.lower().endswith((".mp3", ".wav", ".ogg")))
        result = []
        for f in files:
            m = metadata.get(f, {})
            result.append({
                "filename": f,
                "categories": m.get("categories", []),
                "systems": m.get("systems", []),
            })
        return jsonify(result)
    except Exception:
        return jsonify([])


@bp.get("/api/playlists")
def get_playlists():
    return jsonify(_load_playlists(current_app._get_current_object()))


@bp.post("/api/playlists")
def save_playlist():
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    tracks = data.get("tracks", [])
    if not name:
        return jsonify({"success": False, "error": "name required"}), 400
    app = current_app._get_current_object()
    playlists = _load_playlists(app)
    playlists[name] = tracks
    _save_playlists(app, playlists)
    return jsonify({"success": True})


@bp.delete("/api/playlists/<string:name>")
def delete_playlist(name):
    app = current_app._get_current_object()
    playlists = _load_playlists(app)
    if name not in playlists:
        return jsonify({"success": False, "error": "not found"}), 404
    del playlists[name]
    _save_playlists(app, playlists)
    return jsonify({"success": True})


@bp.post("/api/audio/tag")
def tag_audio():
    data = request.get_json(force=True)
    filename = data.get("filename", "").strip()
    if not filename:
        return jsonify({"success": False, "error": "filename required"}), 400

    audio_dir = os.path.join(current_app.config["UPLOAD_DIR"], "audio")
    if not os.path.exists(os.path.join(audio_dir, secure_filename(filename))):
        return jsonify({"success": False, "error": "file not found"}), 404

    app = current_app._get_current_object()
    metadata = _load_metadata(app)
    metadata[filename] = {
        "categories": data.get("categories", []),
        "systems": data.get("systems", []),
    }
    _save_metadata(app, metadata)
    return jsonify({"success": True})
