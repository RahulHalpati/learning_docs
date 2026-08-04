# 99 · Capstone — Face unlock for `sudo`

> **Level:** Intermediate → Advanced · **Prerequisites:** Sections 01–06
> **Time:** 2–3 h · **Verified (partial):** 2026-07-22 · Python 3.10 · opencv-contrib-python 4.11.0.86 · Ubuntu/Debian

The whole course in one runnable project: a from-scratch face authenticator whose `verify` CLI plugs into PAM to unlock `sudo` — with a password fallback and every safety rail from Section 05.

> 🛑 **SAFETY:** the PAM steps modify system auth. Keep a **root shell open** (`sudo -i`), test in the **`pamtester` sandbox** first, and never remove password auth. The software pipeline below runs **offline with no webcam and no PAM** — do that first.

## What it demonstrates

| Piece | Section |
|-------|---------|
| Haar face **detection** | [02-2](../02_capturing_and_detecting/02_face_detection.md) |
| LBPH **enroll** + **verify** (exit 0/1) | [03-2](../03_recognition_and_enrollment/02_enrollment.md), [03-3](../03_recognition_and_enrollment/03_verify_cli.md) |
| **Threshold** = FAR/FRR trade-off | [01-1](../01_foundations/01_how_face_auth_works.md) |
| `pam_exec` hook, **fail-closed** | [05-1](../05_pam_integration/01_pam_sandbox.md) |
| Safe **`sudo`** wiring + recovery | [05-2](../05_pam_integration/02_wiring_sudo.md) |

## Layout

```
99_project_face_unlock/
├── requirements.txt · gen_samples.py
├── faceunlock/
│   ├── pipeline.py     # detect + normalize (grayscale, resize, equalizeHist)
│   ├── detect.py       # detection demo CLI
│   ├── enroll.py       # train + save an LBPH model
│   ├── verify.py       # verify → exit 0 (accept) / 1 (reject)   ← the PAM contract
│   └── capture.py      # webcam enrollment (your machine)
├── pam/
│   ├── faceunlock-pam.sh   # pam_exec hook (fail-closed, timeout)
│   ├── faceunlock-test     # sandbox PAM service (pamtester)
│   └── install-sudo.sh     # guarded sudo integration (backup + recovery)
├── samples/            # bundled Olivetti faces → runs offline, no webcam (see NOTICE.md)
└── tests/              # offline pytest
```

## Part 1 — run the software pipeline (offline, no webcam, no PAM)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m faceunlock.detect --image samples/detect.png
python -m faceunlock.enroll --images samples/self --model model.yml --no-detect
python -m faceunlock.verify --model model.yml --image samples/self_test.png --no-detect; echo "exit=$?"
python -m faceunlock.verify --model model.yml --image samples/other.png     --no-detect; echo "exit=$?"
```

**Output (real run):**
```
Found 1 face(s):
  box x=37 y=14 w=253 h=253
Enrolled 8 images -> model.yml
ACCEPT (confidence 47.8 < 70.0)
exit=0
REJECT (confidence 87.8 >= 70.0)
exit=1
```

The enrolled identity is accepted (exit 0); a different person is rejected (exit 1). That exit code is the entire contract PAM needs.

## Part 2 — tests

```bash
pytest -q
```

**Output (real run):**
```
....                                                                     [100%]
4 passed in 0.14s
```

Tests assert detection finds a face, the enrolled identity is accepted, another is rejected, and self scores closer than other — all offline.

## Part 3 — enroll your face & wire `sudo` (your machine)

```bash
# enroll from your webcam
python -m faceunlock.capture --out samples/self --count 8
python -m faceunlock.enroll  --images samples/self --model model.yml --no-detect

# deploy where PAM can reach it, then SANDBOX-TEST first (05-1)
#   ... copy to /opt/faceunlock, model to /etc/faceunlock/models/$USER.yml ...
pamtester faceunlock-test "$USER" authenticate      # <-- must pass here first

# only then, with a ROOT SHELL OPEN, wire sudo (05-2)
sudo ./pam/install-sudo.sh
sudo -k; sudo true                                  # test BOTH: face match AND password fallback
```

Follow [05-1](../05_pam_integration/01_pam_sandbox.md) → [05-2](../05_pam_integration/02_wiring_sudo.md) → [05-3](../05_pam_integration/03_hardening_and_fallback.md) exactly; the guarded installer backs up `/etc/pam.d/sudo` and prints the one-command undo.

> ⚠️ **These live steps are hardware-attested, not CI-reproducible** — they need your webcam and modify PAM. The Part 1/2 software core above is what's verified offline.

## What you built vs what to run

You now understand face unlock end to end. For **daily use**, retire this LBPH prototype and run **[Howdy](../06_howdy_the_real_tool/README.md)** — ideally on an **IR** camera, kept updated, `certainty` strict, password fallback intact. This project's value was the understanding; Howdy's is the mileage.

## Extend it

- Add a **blink liveness** check before accepting ([04-2](../04_liveness_and_antispoofing/02_liveness_defenses.md)).
- Swap LBPH for **dlib embeddings** (`face_recognition`) and compare accuracy ([03-1](../03_recognition_and_enrollment/01_embeddings_and_matching.md)).
- Add `logger` audit lines and read them via `journalctl -t faceunlock` ([05-3](../05_pam_integration/03_hardening_and_fallback.md)).
