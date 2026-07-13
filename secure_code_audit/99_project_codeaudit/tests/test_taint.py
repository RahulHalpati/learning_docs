"""Taint must fire when user input reaches a sink, and stay quiet for constants."""

from codeaudit.scanner import scan_source


def ids(source):
    return {f.rule_id for f in scan_source(source)}


def test_tainted_param_reaches_sql_execute():
    src = (
        "def handler(name):\n"
        "    q = name\n"
        "    conn.execute(q)\n"
    )
    assert "CA201" in ids(src)


def test_constant_reaches_execute_is_not_taint():
    src = (
        "def handler():\n"
        "    q = 'SELECT 1'\n"
        "    conn.execute(q)\n"
    )
    assert "CA201" not in ids(src)


def test_request_reaches_open_path_traversal():
    src = (
        "from flask import request\n"
        "def read():\n"
        "    name = request.args.get('name')\n"
        "    return open('/data/' + name).read()\n"
    )
    assert "CA202" in ids(src)


def test_request_reaches_http_ssrf():
    src = (
        "import requests\n"
        "from flask import request\n"
        "def fetch():\n"
        "    url = request.args.get('url')\n"
        "    return requests.get(url).text\n"
    )
    assert "CA203" in ids(src)


def test_open_with_constant_is_quiet():
    src = "def read():\n    return open('/etc/config').read()\n"
    assert "CA202" not in ids(src)
