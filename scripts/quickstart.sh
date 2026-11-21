#!/bin/sh
# Prepare a fully working simulated demo. Run on the Docker host.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"

if [ ! -f .env ]; then
  cp .env.example .env
fi
if [ ! -f config/items.yaml ]; then
  cp config/items.example.yaml config/items.yaml
fi
if [ ! -f config/venues.yaml ]; then
  cp config/venues.paper.example.yaml config/venues.yaml
fi

tmp="$root/.env.tmp"
awk '
  /^ARBSCOUT_ALLOWED_VENUES=/ { print "ARBSCOUT_ALLOWED_VENUES=paper_cheap,paper_dear"; next }
  /^ARBSCOUT_TOS_ACK=/ { print "ARBSCOUT_TOS_ACK=true"; next }
  { print }
' "$root/.env" > "$tmp"
mv "$tmp" "$root/.env"

echo "Ready. Start with: docker compose up --build"
echo "Then open http://localhost:8000 and run a scan."
echo "To try full-auto simulation: switch mode to Full and turn the kill switch off."
