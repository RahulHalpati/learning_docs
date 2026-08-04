# 04-1 · Spoofing attacks

> **Level:** Intermediate · **Prerequisites:** [03-3 · The verify CLI](../03_recognition_and_enrollment/03_verify_cli.md)
> **Time:** 20 min · **Verified:** 2026-07-22 (the attack reuses the verified pipeline)

## Why this matters

It's one thing to be *told* 2D face unlock is spoofable; it's another to watch your own build accept a photo. This lesson is the reality check that makes every "keep the password" rule in this course feel obvious rather than pedantic.

---

## The presentation attack

A **presentation (spoofing) attack** shows the camera a *representation* of the enrolled face instead of the live face:

- **Print attack** — a printed photo of the enrolled user.
- **Screen/replay attack** — the user's face (or a video) on a phone/tablet held to the camera.

Against a plain RGB webcam these often *just work*, because detection and LBPH see pixels, and a good photo's pixels ≈ the real face's pixels.

---

## Why our recognizer can't tell the difference

Our pipeline is: detect a frontal face → normalize → compare histogram distance. **Nothing in it checks that the face is alive or 3D.** A printed photo:
- passes detection (it *is* a frontal face), and
- produces almost the enrolled histogram (same texture), so distance is low → **accept**.

You can see the mechanism with the bundled samples: verifying the enrolled subject's held-out image is *exactly* what a perfect photo of that subject would do — distance **47.8 < 70 → ACCEPT** ([03-3](../03_recognition_and_enrollment/03_verify_cli.md)). The recognizer has no way to know whether those pixels came from a living face or a sheet of paper.

> **Try it on your machine (with your own face):** enroll from your webcam, then hold a printed photo (or your face on another phone) to the camera and run `verify`. On a 2D webcam it will very likely **ACCEPT** the photo. That's not a bug you can patch in the recognizer — it's the ceiling of 2D.

---

## Threat-model consequences

| Attacker has… | 2D webcam unlock | Mitigation |
|---------------|:----------------:|------------|
| a photo of you (social media) | **bypassed** | liveness, IR/depth, + password |
| a video of you | bypassed (even some liveness) | depth, challenge-response, + password |
| nothing, just curiosity | blocked | face unlock is fine here |

This is why, throughout the course, face auth is a **convenience layer** with a **mandatory password fallback** — the fallback is what still stands when the photo wins.

> ⚠️ **Ethics:** demonstrate spoofing only against **your own** enrolled face on **your own** machine, to understand your exposure. Using a photo of someone else to defeat *their* authentication is unauthorized access — illegal and out of scope. This mirrors the [Ethical Hacking](../../ethical_hacking/) course's rule: only test what you own.

---

## Recap & next

- ✅ A presentation attack shows the camera a photo/screen of the enrolled face.
- ✅ Our 2D pipeline has **no liveness check**, so a good photo produces a low distance → accept.
- ✅ The enrolled-image accept (47.8) *is* what a perfect photo attack looks like — the ceiling of 2D.
- ✅ The password fallback is the control that survives a successful spoof.
- ✅ Self-check: which pipeline stage would need to change to reject a photo — detection, recognition, or something new?

→ Next: **[04-2 · Liveness defenses](02_liveness_defenses.md)**

## Exercises

1. Explain why raising the threshold's strictness does **not** defend against a photo attack.

<details>
<summary>Solution</summary>

A photo of *you* produces a genuinely low distance (it looks like you). Tightening the threshold rejects lookalikes and lower-quality matches, but a good photo of the real enrolled face stays under any threshold that still admits the real face. Spoofing needs a *different* signal (liveness/depth), not a stricter distance.
</details>
