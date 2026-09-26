#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"
agent --force --trust "$(build_context)"
