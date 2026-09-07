"""
Uploads a video to Google Drive, organized by plugin name (language).
"""
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth import get_drive_credentials
from config_base import GOOGLE_DRIVE_FOLDER_ID


def upload_to_drive(video_path: Path, plugin_name: str, phrase_data: dict) -> str:
    creds = get_drive_credentials()
    service = build("drive", "v3", credentials=creds)

    filename = f"{plugin_name}-{phrase_data.get('level', 'x')}-{phrase_data['word']}.mp4"
    file_metadata = {
        "name": filename,
        "parents": [GOOGLE_DRIVE_FOLDER_ID] if GOOGLE_DRIVE_FOLDER_ID else [],
    }
    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)

    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return file.get("id")
