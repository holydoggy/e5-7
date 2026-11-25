#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
PORT="${1:-8081}"
SID=$(git -C "$ROOT" config --local user.name)
IMAGE="course-e11e12:$SID"
NAME="e11e12-repair-$PORT"
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --rm --name "$NAME" \
  -p "127.0.0.1:$PORT:8081" \
  --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -e PYTHONPATH=/course/labs/e11e12:/course/labs/e8e10:/course/labs/e11e12/vendor:/app \
  -v "$ROOT:/course" -w /course "$IMAGE" \
  python3 labs/e11e12/repair_server.py --host 0.0.0.0 --port 8081 >/dev/null
sleep 1
echo "started $NAME on 127.0.0.1:$PORT"
