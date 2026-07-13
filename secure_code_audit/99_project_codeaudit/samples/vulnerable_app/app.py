"""An INTENTIONALLY VULNERABLE Flask app — the practice target for the auditor.

Every flaw is annotated with `# VULN:` so you can check what the scanner should
find. DO NOT deploy this or copy these patterns. It exists only to be audited.
The matching secure version is discussed in the course modules.
"""

import hashlib
import os
import pickle
import sqlite3
import subprocess

import requests
import yaml
from flask import Flask, request

app = Flask(__name__)

# VULN: hardcoded secret (CA106, CWE-798)
app.secret_key = "super-secret-key-12345"
API_TOKEN = "sk_live_51H8xExample0000000000"   # VULN: hardcoded secret (CA106)


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    # VULN: SQL injection — f-string into execute (CA107 + taint CA201, CWE-89)
    cur.execute(f"SELECT * FROM users WHERE name = '{username}'")
    # VULN: weak password hashing (CA103, CWE-327)
    digest = hashlib.md5(password.encode()).hexdigest()
    return {"ok": True, "digest": digest}


@app.route("/search")
def search():
    term = request.args.get("q", "")
    conn = sqlite3.connect("app.db")
    query = "SELECT * FROM items WHERE title LIKE '%" + term + "%'"
    # VULN: SQL injection via concatenated variable (taint CA201)
    rows = conn.execute(query).fetchall()
    return {"rows": rows}


@app.route("/ping")
def ping():
    host = request.args.get("host", "127.0.0.1")
    # VULN: command injection — shell=True with user input (CA102 + CA101, CWE-78)
    output = subprocess.check_output("ping -c1 " + host, shell=True)
    os.system("logger " + host)   # VULN: os.system with user input (CA101)
    return output


@app.route("/read")
def read_file():
    name = request.args.get("name", "")
    # VULN: path traversal — user input into open() (taint CA202, CWE-22)
    with open("/var/data/" + name) as fh:
        return fh.read()


@app.route("/fetch")
def fetch():
    url = request.args.get("url", "")
    # VULN: SSRF — user-controlled URL (taint CA203, CWE-918)
    return requests.get(url).text


@app.route("/render")
def render():
    tmpl = request.args.get("t", "")
    # VULN: arbitrary code execution via eval (CA101, CWE-95)
    return str(eval(tmpl))


@app.route("/load", methods=["POST"])
def load():
    blob = request.get_data()
    # VULN: insecure deserialization (CA104, CWE-502)
    obj = pickle.loads(blob)
    cfg = yaml.load(request.args.get("cfg", ""))   # VULN: yaml.load w/o SafeLoader (CA104)
    return {"obj": str(obj), "cfg": str(cfg)}


if __name__ == "__main__":
    # VULN: debug server exposes an RCE console (CA105, CWE-489)
    app.run(host="0.0.0.0", debug=True)
