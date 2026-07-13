# 04-1 · Uploading to YouTube

> **Level:** Beginner → Intermediate · **Time:** 25 min

This is the one part that can't run offline — it needs a real Google account and
channel. It's written as a plain function ([`faceless_studio/publish.py`](../99_project_faceless_studio/faceless_studio/publish.py)),
**not** a graph node, so you call it deliberately after approving a video.

---

## Setup (once)

1. **Google Cloud Console** → create a project → **enable "YouTube Data API v3"**.
2. **Create credentials** → OAuth 2.0 Client ID → application type **Desktop app**
   → download the JSON as `client_secret.json`.
3. Add yourself as a **test user** on the OAuth consent screen (while the app is in
   "testing").
4. Install the libraries:
   ```bash
   pip install google-api-python-client google-auth-oauthlib
   ```

---

## Authorising (cached after first run)

```python
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_authenticated_service(client_secret="client_secret.json", token_file="token.json"):
    creds = None
    if Path(token_file).exists():
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
            creds = flow.run_local_server(port=0)     # opens a browser once
        Path(token_file).write_text(creds.to_json())  # cache the token
    return build("youtube", "v3", credentials=creds)
```

First run opens a browser to consent; after that the cached `token.json` is reused
and refreshed automatically. Request the **minimum scope** (`youtube.upload`).

---

## Uploading — private by default

```python
def upload_video(video_path, *, title, description, tags=None,
                 category_id="27", privacy="private",
                 made_for_kids=False, publish_at=None):
    youtube = get_authenticated_service()
    status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": made_for_kids}
    if publish_at:
        status["publishAt"] = publish_at          # ISO 8601, schedules a public release
    body = {
        "snippet": {"title": title[:100], "description": description[:5000],
                    "tags": (tags or [])[:500], "categoryId": category_id},
        "status": status,
    }
    media_body = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media_body)
    response = None
    while response is None:
        _status, response = request.next_chunk()   # resumable upload loop
    return response
```

Wire it to the metadata the pipeline already wrote:

```python
import json
from faceless_studio.publish import upload_video

meta = json.load(open("out/big-o-notation-for-beginners/metadata.json"))
upload_video(
    "out/big-o-notation-for-beginners/video.mp4",
    title=meta["title"], description=meta["description"], tags=meta["tags"],
    privacy="private",        # review on YouTube, THEN flip to public
)
```

---

## The non-negotiables

- **Default to `private`.** Upload private, watch it on YouTube, *then* publish or
  schedule. Never let a pipeline flip things public automatically.
- **Disclose AI content.** In YouTube Studio (or via the API's altered-content
  fields), mark videos with synthetic audio/visuals. This is required, not optional.
- **`categoryId="27"`** is Education; pick the right one for your niche.
- **Quota:** an upload costs ~1600 units of the default 10,000/day quota — a few
  uploads a day before you need to request more. Don't build anything that hammers
  it.
- **Scheduling:** set `publish_at` to an ISO 8601 UTC timestamp (e.g.
  `"2026-07-10T09:00:00Z"`) with `privacy="private"` to schedule a public release.

---

## Recap

- Upload via **YouTube Data API v3** with an OAuth desktop client; the token caches
  after the first browser consent.
- It's a **deliberate function call**, not a node — you run it after approving the
  video.
- **Private by default**, **disclose AI content**, mind the **quota**, and use
  `publish_at` to schedule.

## Self-check

1. Why is `upload_video` deliberately *not* part of the LangGraph pipeline?
2. What's the safe default for `privacy`, and what's the workflow from there?

<details>
<summary>Answers</summary>

1. Publishing is outward-facing and effectively irreversible for a public video; it
   should require a separate, conscious human action rather than firing at the end
   of every graph run.
2. `"private"` — upload privately, review the real video on YouTube, then manually
   publish or set a `publish_at` schedule.

</details>

---

**Next → [04-2 · CLI & scheduling a daily run](02_cli_and_scheduling.md)**
