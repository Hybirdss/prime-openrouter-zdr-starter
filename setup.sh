#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 -I "$ROOT/scripts/manage.py" setup "$@"
