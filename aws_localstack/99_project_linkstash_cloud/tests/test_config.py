"""Config-from-AWS tests: Secrets Manager + SSM Parameter Store, against LocalStack."""

import os

import pytest

from app.config import load_config, load_secret_key, load_table_name

pytestmark = pytest.mark.skipif(
    not os.environ.get("AWS_ENDPOINT_URL"),
    reason="set AWS_ENDPOINT_URL=http://localhost:4566 and apply infra first",
)


def test_secret_loads_from_secrets_manager():
    assert load_secret_key() == "dev-secret-rotate-me"


def test_table_name_loads_from_ssm():
    assert load_table_name() == "links"


def test_load_config_bundles_both():
    cfg = load_config()
    assert cfg["secret_key"] == "dev-secret-rotate-me"
    assert cfg["links_table"] == "links"
