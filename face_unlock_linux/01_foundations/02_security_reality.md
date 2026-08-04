# 01-2 · The security reality

> **Level:** Beginner · **Prerequisites:** [01-1 · How face auth works](01_how_face_auth_works.md)
> **Time:** 20 min · **Verified:** 2026-07-22 (concepts)

## Why this matters

The most important lesson in this course isn't code — it's calibrating your trust. Face unlock *feels* strong, so people wire it into everything and drop their guard. A clear threat model tells you exactly what it protects against (a curious housemate) and what it doesn't (a determined attacker with a photo of you).

---

## The core weakness: a 2D camera can't tell a face from a photo

An RGB webcam sees a flat image. Your live face and a **printed photo** of your face — or your face on someone's phone screen — produce nearly the same pixels. So the classic attack is trivially cheap:

> **Presentation attack (spoofing):** hold a photo of the enrolled user to the camera. To plain 2D recognition, it *is* the enrolled user.

You'll do exactly this in [04-1](../04_liveness_and_antispoofing/01_spoofing_attacks.md) — your own enrolled face, printed or on a screen, unlocks your own build. That's not a bug in our code; it's the fundamental limit of 2D.

---

## What actually raises the bar

| Defense | Helps against | Still beaten by |
|---------|---------------|-----------------|
| **IR camera** (Howdy's target) | flat photos/screens (no depth/heat) | high-effort 3D masks; IR photos |
| **Liveness / anti-spoofing** (blink, motion) | static photos | video replay, sophisticated attacks |
| **Depth sensing** (structured light, like Face ID) | photos and most masks | well-funded attackers |
| **A second factor** (password/PIN) | *everything above's failure* | — |

Consumer phone face unlock (Face ID) is comparatively strong because it uses **depth**, not RGB. A laptop webcam does not. Howdy with an **IR** camera sits in between. Our from-scratch RGB build is at the bottom — perfect for learning, weak as a lone guard.

---

## The rules we follow

Because of all this, the course never treats face unlock as a sole factor:

1. **Face auth is `sufficient`, never `required` and alone.** If the face check fails *or is skipped*, you fall through to the password. (This is also what keeps you from being locked out — Section 05.)
2. **Password auth is never removed.** It's the floor.
3. **We fail closed.** No face, camera error, or timeout → *reject* → password, never "let them in because something broke."
4. **We're explicit about the threat model.** Face unlock here defends against casual, opportunistic access — not a targeted attacker who has your photo and physical access.

---

## A quick threat-model sentence

> "Face unlock stops my coworker from poking at my unlocked-looking laptop; it does **not** stop someone who has a photo of me and wants in."

If your threat model needs more than the first clause, face unlock is the *wrong* primary control — use it as convenience on top of a strong password/2FA, exactly as we wire it.

---

## Recap & next

- ✅ A 2D webcam can't distinguish your face from a **photo** of it — spoofing is cheap.
- ✅ IR, liveness, and depth raise the bar; only a **second factor** covers their failure.
- ✅ Our rules: face is `sufficient` not sole, password always kept, **fail closed**, threat model stated.
- ✅ Self-check: why is "fail closed" both a security *and* a lockout-safety property?

→ Next: **[01-3 · Environment & safety](03_environment_and_safety.md)**

## Exercises

1. Classify each as adequately protected by webcam face unlock or not: (a) resuming a locked screen at home, (b) `sudo` on a shared server, (c) decrypting a laptop at a border crossing.

<details>
<summary>Solution</summary>

(a) Reasonable *convenience* with a password fallback. (b) No — a shared/hostile environment with real attackers; webcam face unlock adds little and a photo could suffice. (c) Absolutely not — a targeted adversary with resources; biometrics can even be compelled. Match the control to the threat.
</details>
