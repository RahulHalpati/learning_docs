"""Each rule must fire on a bad snippet and stay quiet on the safe equivalent."""

from codeaudit.scanner import scan_source


def ids(source):
    return {f.rule_id for f in scan_source(source)}


def test_dangerous_call_eval():
    assert "CA101" in ids("x = eval(data)")
    assert "CA101" not in ids("x = int(data)")


def test_shell_true():
    assert "CA102" in ids("import subprocess\nsubprocess.run(cmd, shell=True)")
    assert "CA102" not in ids("import subprocess\nsubprocess.run(['ls', '-l'])")


def test_weak_hash():
    assert "CA103" in ids("import hashlib\nh = hashlib.md5(p).hexdigest()")
    assert "CA103" not in ids("import hashlib\nh = hashlib.sha256(p).hexdigest()")


def test_insecure_deserialization():
    assert "CA104" in ids("import pickle\nobj = pickle.loads(blob)")
    assert "CA104" in ids("import yaml\nc = yaml.load(text)")
    assert "CA104" not in ids("import yaml\nc = yaml.safe_load(text)")
    assert "CA104" not in ids("import yaml\nc = yaml.load(text, Loader=yaml.SafeLoader)")


def test_flask_debug():
    assert "CA105" in ids("app.run(debug=True)")
    assert "CA105" not in ids("app.run(debug=False)")


def test_hardcoded_secret():
    assert "CA106" in ids('password = "hunter2boss"')
    assert "CA106" in ids('API_TOKEN = "sk_live_abc123456"')
    assert "CA106" not in ids('password = os.environ["PW"]')


def test_sql_string_build():
    assert "CA107" in ids('cur.execute(f"SELECT * FROM t WHERE a = {x}")')
    assert "CA107" in ids('cur.execute("SELECT * FROM t WHERE a = " + x)')
    assert "CA107" not in ids('cur.execute("SELECT * FROM t WHERE a = ?", (x,))')


def test_syntax_error_is_reported_not_raised():
    found = scan_source("def (:\n  pass")
    assert any(f.rule_id == "CA000" for f in found)
