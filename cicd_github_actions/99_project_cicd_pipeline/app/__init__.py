"""linkstash — a tiny link-shortener API used to demonstrate a full CI/CD pipeline.

The app is deliberately small; the *pipeline* around it is the point. Pure logic
lives in `core.py` (fast to unit-test and lint); the HTTP layer is in `main.py`.
"""

__version__ = "1.2.0"
