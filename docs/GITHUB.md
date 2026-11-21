# Getting a hosted website and an APK without local tooling

You do not need Node, Java, Android Studio or Docker on your own machine. GitHub Actions does the builds.

## 1. Create the repository

On a PC with `git` and the [GitHub CLI](https://cli.github.com) installed:

```sh
sh scripts/setup-github.sh arbscout --private
```

Or create an empty repo on GitHub manually and push the folder:

```sh
git init -b main
git add .
git commit -m "ArbScout"
git remote add origin https://github.com/YOU/arbscout.git
git push -u origin main
```

`.gitignore` keeps `.env`, `node_modules/`, `android/` and built APKs out of the repo.

## 2. Website

`deploy-pages.yml` deploys `web/` to GitHub Pages on every push to `main`/`master`.

- In the repo: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
- The URL appears under **Settings → Pages** and in the Actions run summary.
- The deployed site runs the offline demo until you point it at a backend: open `https://YOU.github.io/arbscout/?api=https://your-backend:8000` once. The value is saved locally.

Alternatives if you prefer another host: `netlify.toml` and `vercel.json` are included — connect the repo to Netlify or Vercel and they will serve `web/` directly.

Or host just the static site anywhere Docker runs:

```sh
docker compose -f docker-compose.web.yml up --build
# http://localhost:8080
```

## 3. APK

Two choices:

- **Artifact:** Actions → `Release website + APK` → *Run workflow*. Download `arbscout-apk` when it finishes.
- **Release:** push a tag, e.g. `git tag v0.1.0 && git push --tags`. The same workflow publishes a GitHub Release containing both `app-debug.apk` and `arbscout-website.zip`.

The workflow installs Node 20, JDK 17 and the Android SDK, generates the Capacitor Android project, syncs `web/`, and runs `assembleDebug`.

Install the APK on Android, then open it once with `?api=https://your-backend:8000` appended to its start URL if you want it to talk to your backend. Android requires HTTPS for cleartext-by-default restrictions; `allowMixedContent` is enabled in `capacitor.config.json` for local testing.

## 4. Backend image

`docker-publish.yml` pushes the backend to GitHub Container Registry on a `v*` tag or manual dispatch:

```
ghcr.io/YOU/arbscout:latest
```

Run it anywhere Docker is available and point the hosted website/APK at its public HTTPS URL with `?api=`.

## 5. Full stack

The backend is still the Docker Compose service:

```sh
sh scripts/quickstart.sh
docker compose up --build
```

GitHub Pages / Netlify / Vercel host only the front end; they do not run the Python API.
