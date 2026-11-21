# Asset credits

The front end uses **real, licensed design assets** rather than generated placeholder art.

| Asset | File | Source | License |
| --- | --- | --- | --- |
| 3D model "Camera 01" | `web/assets/models/camera/` | [Poly Haven](https://polyhaven.com/a/camera_01) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| HDRI "Blocky Photo Studio" (1k) | `web/assets/hdri/blocky_photo_studio_1k.hdr` | [Poly Haven](https://polyhaven.com/a/blocky_photo_studio) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| Inter variable font (latin) | `web/assets/fonts/inter-latin-variable.woff2` | [Google Fonts](https://fonts.google.com/specimen/Inter) | [SIL OFL 1.1](https://openfontlicense.org/) |
| three.js + loaders | `web/vendor/` | [three.js](https://threejs.org/) | MIT |
| App icon | `web/assets/icon.svg` | Original for this project | MIT |

No design MCP server or design skill was available in the build session. Assets were fetched from the sources above and vendored locally so the web app and APK work offline. The 3D object is a real glTF model with PBR textures, lit by a real HDRI environment map; scroll position drives its rotation, tilt, camera distance and vertical drift.

Previously considered `DamagedHelmet.glb` was removed because its upstream license chain includes a non-commercial term.
