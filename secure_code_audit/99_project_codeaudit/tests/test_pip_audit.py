import subprocess

def audit_pip_vulnerable():
    result = subprocess.run(
        ["pip-audit", "-r", "samples/vulnerable_app/requirements.txt", "--formate", "json"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 1
    assert "flask" in result.stdout