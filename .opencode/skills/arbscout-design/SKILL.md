---
name: arbscout-design
description: Use when changing ArbScout's front-end design, 3D hero, PWA shell, or asset set. Covers the shared web source of truth, licensed real-asset rules, design tokens, and verification.
---

# ArbScout design pipeline

This skill applies to `web/` and the Capacitor wrapper. Never create a separate UI for Android — `web/` is the only front end.

## Hard constraints

1. `web/` is the single source of truth. Both the PWA and the APK bundle it verbatim.
2. Use **real, licensed assets** (CC0 / OFL / MIT). No fabricated placeholder art, no proprietary Apple assets, no licence-laundering.
3. Record every asset in `ASSETS.md` with source and licence before it ships.
4. The 3D scene uses a real glTF/PBR model and a real HDRI environment map. Scroll position drives rotation, tilt, camera distance and drift. Do not replace them with CSS fakes.
5. No stealth, CAPTCHA solving, or anti-detection code belongs anywhere in the front end.

## Design tokens

- Background `#050507`, surfaces `rgba(255,255,255,0.045)`, hairline borders `rgba(255,255,255,0.1)`.
- Ink `#f4f6fb`, muted `#929aae`, accents mint `#7cf7d4` and blue `#6c8cff`.
- Inter variable font, 300–700, tight letter-spacing on display sizes.
- 22px radii, 18px blurred glass panels, spring-like transitions.
- Respect `prefers-reduced-motion`.

## Layout contract

- `.hero` is 340vh with a 100vh sticky canvas and three scroll steps.
- `.console` exposes live stats, opportunities, mode switch and kill switch.
- `.research` explains valuation; `.audit-section` shows the decision log.

## Adding or replacing a 3D asset

1. Download from a CC0 source and place under `web/assets/models/`.
2. Keep relative URIs intact (`.gltf` + `.bin` + `textures/`).
3. Update the loader path in `web/app.js` and the attribution in `ASSETS.md` and `web/index.html`.
4. Add every new file to `web/sw.js` `CORE`/`TEXTURES`.
5. Run `sh scripts/verify.sh`.

## Validate

```sh
sh scripts/verify.sh
```

The check is POSIX `sh` and needs no Node or Python. Full visual verification requires a browser with WebGL and a running backend.
