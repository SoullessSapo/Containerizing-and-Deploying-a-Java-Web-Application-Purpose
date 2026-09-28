#!/usr/bin/env bash
# Builds the jar and the image, starts three isolated containers of the same
# image on ports 34000-34002 and checks that each one answers on its own.
#
# Usage: DOCKERHUB_USER=<dockerhub-user> scripts/local-demo.sh [--clean]
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE="${DOCKERHUB_USER:-dockerhub-user}/virtualization-lab:1.0"
NAMES=(virtualization-lab-1 virtualization-lab-2 virtualization-lab-3)
PORTS=(34000 34001 34002)

if [ "${1:-}" = "--clean" ]; then
  docker rm -f "${NAMES[@]}" 2>/dev/null || true
  exit 0
fi

mvn -q clean package
docker build -t "$IMAGE" .
docker rm -f "${NAMES[@]}" 2>/dev/null || true

for i in "${!NAMES[@]}"; do
  docker run -d --name "${NAMES[$i]}" -e PORT=9000 -p "${PORTS[$i]}:9000" "$IMAGE" >/dev/null
done

for i in "${!NAMES[@]}"; do
  for _ in $(seq 1 60); do
    curl -fs "http://localhost:${PORTS[$i]}/greeting" >/dev/null && break
    sleep 1
  done
  scripts/smoke-test.sh "http://localhost:${PORTS[$i]}" "Container$((i + 1))"
done

docker ps --filter "name=virtualization-lab-" \
  --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
