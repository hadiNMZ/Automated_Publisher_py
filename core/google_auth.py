"""
Shared Google OAuth flow for Drive + YouTube uploads.

IMPORTANT: Drive and YouTube scopes must be authorized SEPARATELY.
Google's OAuth infrastructure rejects requesting drive.file and
youtube.upload together in one authorization request ("scopes that
cannot be requested together") because they go through different
verification tracks. So each gets its own flow and its own cached
token file -- you'll see two separate browser consent screens the
first time (one per scope), never combined into one.
"""
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from config_base import GOOGLE_CLIENT_SECRETS_FILE, ROOT_DIR

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

DRIVE_TOKEN_FILE = ROOT_DIR / "token_drive.json"
YOUTUBE_TOKEN_FILE = ROOT_DIR / "token_youtube.json"


def _get_credentials(scopes: list[str], token_file) -> Credentials:
    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CLIENT_SECRETS_FILE, scopes)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json())

    return creds


def get_drive_credentials() -> Credentials:
    return _get_credentials(DRIVE_SCOPES, DRIVE_TOKEN_FILE)


def get_youtube_credentials() -> Credentials:
    return _get_credentials(YOUTUBE_SCOPES, YOUTUBE_TOKEN_FILE)
