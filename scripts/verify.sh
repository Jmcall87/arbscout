#!/bin/sh
# Static sanity check: no Python/Node required.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
missing=0

check() {
  if [ ! -e "$root/$1" ]; then
    echo "MISSING: $1"
    missing=1
  fi
}

for f in \
  README.md ASSETS.md docker-compose.yml .env.example capacitor.config.json package.json \
  backend/Dockerfile backend/requirements.txt \
  backend/app/main.py backend/app/router.py backend/app/scanner.py \
  backend/app/execution/executor.py backend/app/execution/policies.py \
  backend/app/normalization.py backend/app/valuation.py backend/app/db.py \
  backend/app/research/market.py backend/app/browser/session.py \
  backend/app/venues/base.py backend/app/venues/api_adapter.py \
  backend/app/venues/browser_adapter.py backend/app/venues/paper_adapter.py \
  backend/app/venues/registry.py backend/tests/test_core.py \
  config/venues.example.yaml config/venues.paper.example.yaml config/items.example.yaml \
  docs/ARCHITECTURE.md docs/GITHUB.md scripts/quickstart.sh scripts/setup-github.sh \
  netlify.toml vercel.json web/Dockerfile docker-compose.web.yml \
  web/index.html web/styles.css web/app.js web/manifest.webmanifest web/sw.js \
  web/assets/icon.svg web/assets/fonts/inter-latin-variable.woff2 \
  web/assets/hdri/blocky_photo_studio_1k.hdr \
  web/assets/models/camera/Camera_01_1k.gltf web/assets/models/camera/Camera_01.bin \
  web/vendor/three.module.js web/vendor/GLTFLoader.js web/vendor/RGBELoader.js \
  .github/workflows/build-apk.yml .github/workflows/test.yml \
  .github/workflows/release.yml .github/workflows/deploy-pages.yml \
  .github/workflows/docker-publish.yml; do
  check "$f"
done

if [ "$missing" -eq 0 ]; then
  echo "OK: ArbScout project structure is complete"
else
  echo "Project is incomplete"
  exit 1
fi
