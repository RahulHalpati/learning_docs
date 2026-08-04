# 04-2 · Liveness defenses

> **Level:** Intermediate · **Prerequisites:** [04-1 · Spoofing attacks](01_spoofing_attacks.md)
> **Time:** 25 min · **Verified:** 2026-07-22 (concepts; techniques described, not all offline-reproducible)

## Why this matters

If a photo beats 2D recognition, the fix isn't better recognition — it's proving the face is a **live, present person**. That's **liveness detection** (anti-spoofing). Knowing the techniques, and honestly where each breaks, tells you how much a given setup can be trusted.

---

## Software liveness (works on a normal webcam)

| Technique | Idea | Beaten by |
|-----------|------|-----------|
| **Blink detection** | track eyes over frames; require a natural blink | a video replay of you blinking |
| **Motion / head turn** | require small movement between frames | video replay; a waved photo |
| **Challenge–response** | ask "turn left", "blink now" at random | real-time deepfake / prepared video |
| **Texture/frequency analysis** | printed/screen faces have tell-tale moiré, reflections, flatness | high-quality prints, matte screens |

These raise the bar against a *static photo* meaningfully and cost nothing but code. A rough blink check, for example, watches the eye-aspect-ratio across several frames (via facial landmarks) and only proceeds if it sees eyes close then open. But **video replay defeats most software liveness** — if the attacker can play a video of you blinking on cue, the signal is there.

> **Tip:** even simple liveness (require a blink within N frames) turns the trivial "hold up a photo" attack into "produce a video and time it" — a real increase in effort for casual attackers. It is *mitigation*, not a guarantee.

---

## Hardware liveness (the real jump)

| Sensor | Why it beats photos |
|--------|--------------------|
| **IR camera** (Howdy's target) | sees heat/near-IR; a printed photo and most screens don't reproduce the IR signature; also works in the dark |
| **Depth / structured light** (Face ID) | measures 3D shape; a flat photo has no depth, so it fails instantly |
| **Multi-camera stereo** | triangulates depth from two lenses |

This is the biggest single improvement. A plain laptop RGB webcam has none of it; **Howdy with an IR camera** does, which is why Section 06's setup is materially stronger than our from-scratch RGB build. Even so, depth/IR are beaten by sufficiently sophisticated 3D masks — "harder", never "impossible".

---

## The honest hierarchy

```
RGB webcam, no liveness        ← our teaching build: convenience only
  + software liveness (blink)  ← stops casual photo attacks
  + IR camera (Howdy)          ← stops flat photos/screens; works in dark
  + depth (Face ID-class)      ← stops photos and most masks
  + a second factor (password) ← the floor under ALL of the above
```

Every rung up costs money or code and raises the attacker's effort. **None removes the need for the password fallback** — which is exactly why our design keeps it, always.

---

## What we implement vs point to

- **This course's build:** RGB, **no liveness** — deliberately, so the weakness is visible and the lesson lands. We compensate with `sufficient` + password fallback + fail-closed.
- **Production:** use **Howdy with an IR camera** ([Section 06](../06_howdy_the_real_tool/README.md)); add software liveness if you stay on RGB; never drop the second factor.

---

## Recap & next

- ✅ Liveness proves a *live, present* face — the defense photos can't pass.
- ✅ Software liveness (blink/motion/challenge) stops casual photo attacks but not video replay.
- ✅ **IR/depth** cameras are the real jump; Howdy targets IR.
- ✅ No rung removes the **password fallback** — it's the floor.
- ✅ Self-check: why does an IR camera defeat a printed photo that fools an RGB camera?

→ Next: **[05 · PAM integration](../05_pam_integration/README.md)**

## Exercises

1. Rank by attacker effort to bypass: (a) RGB no-liveness, (b) RGB + blink, (c) IR camera, (d) depth. Then note which single addition protects *all* of them.

<details>
<summary>Solution</summary>

Effort ascends a → b → c → d (photo → timed video → IR-defeating print/mask → 3D mask). The single addition that protects all of them is the **password/second factor** — it's the floor that holds when any biometric rung is bypassed.
</details>
