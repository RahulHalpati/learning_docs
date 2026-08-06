"""Backend tests for the streaming chat app — run with the mock backend (no key).

    LLM_BACKEND=mock python test_app.py

Drives the FastAPI app in-process with TestClient (no running server needed),
exercising the HTTP index, a streamed reply, multi-turn memory, and the stop
feature. This is the exact harness used to verify the project in the guide.
"""
import os

os.environ.setdefault("LLM_BACKEND", "mock")    # force the no-key backend

from fastapi.testclient import TestClient       # noqa: E402  (import after env is set)

import main                                      # noqa: E402


def run() -> None:
    with TestClient(main.app) as client:
        # 1. the index page is served
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        print(f"GET / -> {r.status_code} {r.headers['content-type']} len {len(r.text)}")

        # 2. a streamed reply, then a second turn on the same connection
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_text("Hello there")
            reply, n = "", 0
            while True:
                m = ws.receive_json()
                if m["type"] == "token":
                    reply += m["content"]
                    n += 1
                elif m["type"] == "end":
                    print(f"turn1: {n} tokens, stopped={m['stopped']}")
                    break
            assert n > 0 and reply
            print("turn1 reply starts:", repr(reply[:40]))

            ws.send_text("And again")
            while True:
                m = ws.receive_json()
                if m["type"] == "end":
                    print("turn2 stopped=", m["stopped"])
                    break

        # 3. stop a reply mid-stream
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_text("Tell me a long story")
            ws.send_text("__stop__")
            tokens = 0
            while True:
                m = ws.receive_json()
                if m["type"] == "token":
                    tokens += 1
                elif m["type"] == "end":
                    print(f"stop test: {tokens} tokens before end, stopped={m['stopped']}")
                    assert m["stopped"] is True
                    break

    print("ALL PROJECT TESTS PASSED")


if __name__ == "__main__":
    run()
