"""Upload a finished video to YouTube via the YouTube Data API v3.

This is the ONE part of the pipeline that cannot run offline: it needs a Google
Cloud OAuth client and a real channel. It is written as a normal function so the
graph stays testable — you only call it after a human has approved the video.

Setup (once):
  1. Google Cloud Console → enable "YouTube Data API v3".
  2. Create an OAuth 2.0 Client ID (Desktop app) → download `client_secret.json`.
  3. pip install google-api-python-client google-auth-oauthlib
  4. First run opens a browser to authorise; the token is cached in `token.json`.

Quota note: an upload costs ~1600 units of the default 10,000/day quota, so
you can upload a handful of videos per day before requesting more.
"""

from __future__ import annotations

import os
from pathlib import Path

# YouTube requires the upload scope. Keep it minimal.
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_authenticated_service(
    client_secret: str = "client_secret.json",
    token_file: str = "token.json",
):
    """Return an authorised YouTube API client, caching the OAuth token."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if Path(token_file).exists():
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
            creds = flow.run_local_server(port=0)
        Path(token_file).write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_path: str,
    *,
    title: str,
    description: str,
    tags: list[str] | None = None,
    category_id: str = "27",            # 27 = Education
    privacy: str = "private",           # start private; flip to "public" when happy
    made_for_kids: bool = False,
    publish_at: str | None = None,      # ISO 8601 to schedule (privacy must be "private")
) -> dict:
    """Upload `video_path` and return the created video resource.

    `privacy="private"` is the safe default — review it on YouTube, then publish.
    Set `publish_at` (e.g. "2026-07-10T09:00:00Z") to schedule a public release.
    """
    from googleapiclient.http import MediaFileUpload

    if not Path(video_path).exists():
        raise FileNotFoundError(video_path)

    youtube = get_authenticated_service(
        client_secret=os.environ.get("YT_CLIENT_SECRET", "client_secret.json"),
        token_file=os.environ.get("YT_TOKEN_FILE", "token.json"),
    )

    status: dict = {"privacyStatus": privacy, "selfDeclaredMadeForKids": made_for_kids}
    if publish_at:
        status["publishAt"] = publish_at

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": (tags or [])[:500],
            "categoryId": category_id,
        },
        "status": status,
    }

    media_body = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media_body
    )

    response = None
    while response is None:
        _status, response = request.next_chunk()
    return response
