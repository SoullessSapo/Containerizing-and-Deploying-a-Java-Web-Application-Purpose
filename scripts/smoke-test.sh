#!/usr/bin/env bash
# Verifies that a running instance of the service answers correctly.
#
# Usage: scripts/smoke-test.sh <base-url> [name]
#   scripts/smoke-test.sh http://localhost:6000 Pedro
#   scripts/smoke-test.sh http://<ec2-public-dns>:8080 AWS
set -euo pipefail

BASE_URL="${1:?Usage: $0 <base-url> [name]}"
NAME="${2:-Smoke}"
EXPECTED="Hello, ${NAME}!"

ACTUAL="$(curl -fsS --max-time 10 "${BASE_URL%/}/greeting?name=${NAME}")"

if [ "$ACTUAL" = "$EXPECTED" ]; then
  echo "PASS ${BASE_URL%/}/greeting?name=${NAME} -> ${ACTUAL}"
else
  echo "FAIL ${BASE_URL%/}/greeting?name=${NAME}: expected '${EXPECTED}' but got '${ACTUAL}'" >&2
  exit 1
fi
