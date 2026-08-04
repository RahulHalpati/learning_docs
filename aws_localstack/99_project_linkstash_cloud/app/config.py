"""Load runtime config from AWS — secrets from Secrets Manager, plain config from
SSM Parameter Store — instead of hardcoding it (the lesson from the code-audit
course, now done the AWS way).

Everything degrades to env-var defaults if the services aren't reachable, so the
app still runs before the infra is applied.
"""

from __future__ import annotations

import os

from .storage import client

SECRET_NAME = os.environ.get("SECRET_NAME", "linkstash/secret-key")
TABLE_PARAM = os.environ.get("TABLE_PARAM", "/linkstash/links-table")


def load_secret_key() -> str:
    """Fetch the app secret from Secrets Manager (never from code)."""
    try:
        sm = client("secretsmanager")
        return sm.get_secret_value(SecretId=SECRET_NAME)["SecretString"]
    except Exception:
        return os.environ.get("SECRET_KEY", "fallback-dev-key")


def load_table_name() -> str:
    """Fetch the (non-secret) table name from SSM Parameter Store."""
    try:
        ssm = client("ssm")
        return ssm.get_parameter(Name=TABLE_PARAM)["Parameter"]["Value"]
    except Exception:
        return os.environ.get("LINKS_TABLE", "links")


def load_config() -> dict:
    return {"secret_key": load_secret_key(), "links_table": load_table_name()}
