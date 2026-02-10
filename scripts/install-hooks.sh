#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$ROOT_DIR/.git/hooks"

mkdir -p "$HOOKS_DIR"
cp "$ROOT_DIR/.githooks/pre-push" "$HOOKS_DIR/pre-push"
chmod +x "$HOOKS_DIR/pre-push"

echo "Hook pre-push instalado en $HOOKS_DIR/pre-push"
