# 03-3 · The verify CLI

> **Level:** Intermediate · **Prerequisites:** [03-2 · Enrollment](02_enrollment.md)
> **Time:** 30 min · **Verified:** 2026-07-22 (opencv-contrib-python 4.11.0.86, bundled samples)

## Why this matters

This is the keystone. PAM doesn't understand faces — it understands **exit codes**. So we wrap recognition in a CLI that prints a verdict and exits **0 (accept)** or **1 (reject)**. That one contract is what lets `pam_exec` turn "your face matched" into "you're authenticated" ([Section 05](../05_pam_integration/README.md)).

---

## The contract: exit 0 = accept

```python
# faceunlock/verify.py  (core)
import sys, cv2
from .pipeline import prepare_face, DEFAULT_THRESHOLD
from .enroll import ENROLLED_LABEL

def verify_face(recognizer, face, threshold):
    label, confidence = recognizer.predict(face)          # confidence = distance
    accepted = (label == ENROLLED_LABEL) and (confidence < threshold)
    return accepted, confidence

# ... load model, get a face (image or webcam) ...
if face is None:
    print("REJECT: no face found", file=sys.stderr); sys.exit(1)   # FAIL CLOSED
accepted, conf = verify_face(recognizer, face, threshold)
sys.exit(0 if accepted else 1)
```

Two design rules baked in:
- **Fail closed:** no face / camera error / timeout → exit 1 (→ password). Never exit 0 on error.
- **Silent on success path for PAM:** diagnostics go to stderr; PAM only cares about the exit code.

---

## Run it — accept the enrolled user

```bash
python -m faceunlock.enroll --images samples/self --model model.yml --no-detect
python -m faceunlock.verify --model model.yml --image samples/self_test.png --no-detect
echo "exit=$?"
```

**Output (real run):**
```
ACCEPT (confidence 47.8 < 70.0)
exit=0
```

## Run it — reject a different person

```bash
python -m faceunlock.verify --model model.yml --image samples/other.png --no-detect
echo "exit=$?"
```

**Output (real run):**
```
REJECT (confidence 87.8 >= 70.0)
exit=1
```

There it is: the enrolled identity scores **47.8** (accept, exit 0); a different person scores **87.8** (reject, exit 1). The threshold **70** sits in the gap. On your machine, drop `--image` and it reads the webcam instead.

---

## Tuning the threshold = choosing your FAR/FRR

The threshold is the security dial from [01-1](../01_foundations/01_how_face_auth_works.md), now concrete:

| Threshold | self (47.8) | other (87.8) | Effect |
|-----------|:-----------:|:------------:|--------|
| **40** | reject | reject | too strict — locks *you* out (high FRR) |
| **70** | accept | reject | ✅ the sweet spot for these samples |
| **100** | accept | accept | too loose — lets others in (high FAR) |

> ⚠️ **These numbers are dataset- and lighting-specific.** 47.8/87.8 come from the bundled samples. With your webcam and your face, run a few accept/reject trials and pick a threshold in *your* gap. Bias toward **stricter** (lower) — a false reject just means typing your password; a false accept means someone else is in.

Pass `--threshold N` to experiment without re-enrolling.

---

## This CLI is the whole product

Everything from here reuses this exact command:
- **Sandbox** ([05-1](../05_pam_integration/01_pam_sandbox.md)): `pam_exec` runs it against a test PAM service via `pamtester`.
- **sudo** ([05-2](../05_pam_integration/02_wiring_sudo.md)): the same `pam_exec` line in `/etc/pam.d/sudo`.
- **Tests** (capstone): `verify_face()` is asserted on the sample faces.

One artifact, built once, wired three ways.

---

## Recap & next

- ✅ The verifier's contract is **exit 0 = accept, exit 1 = reject** — what PAM consumes.
- ✅ **Fail closed:** any error/no-face → reject → password fallback.
- ✅ Verified: enrolled **47.8 → ACCEPT/0**, other **87.8 → REJECT/1**, threshold **70**.
- ✅ The threshold *is* your FAR/FRR choice — bias stricter; tune to your own gap.
- ✅ Self-check: why do we send diagnostics to stderr and reserve the exit code for the verdict?

→ Next: **[04 · Liveness & anti-spoofing](../04_liveness_and_antispoofing/README.md)**

## Exercises

1. Run verify on `samples/self_test.png` with `--threshold 40` and then `--threshold 100`. Confirm the accept/reject flips and map each to FAR or FRR.

<details>
<summary>Solution</summary>

`--threshold 40`: self (47.8) is now **rejected** → a false reject (FRR ↑). `--threshold 100`: `other` (87.8) is now **accepted** → a false accept (FAR ↑). The middle (70) is the only setting that's correct for both — exactly the trade-off from 01-1.
</details>
