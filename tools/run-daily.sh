#!/bin/bash
# One day's synthetic traffic, run by launchd on a Mac.
#
# The GitHub Actions version of this needs an OIDC role, which needs IAM
# permissions this account does not have. Until somebody with them creates one,
# this is the path that works: it uses whatever credentials are already in
# ~/.aws, which on an SSO setup are refreshed from the cached login token
# without anybody typing anything.
#
# It is honest about the trade. A laptop is asleep sometimes, so days will be
# missed, and a missed day is a gap in the history rather than a wrong number.
# The monitor compares against the median of the days it has, so gaps cost
# resolution and nothing else -- which is the right way round.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$REPO/.prreview/cache/traffic.log"
mkdir -p "$(dirname "$LOG")"

exec >>"$LOG" 2>&1
echo "--- $(date -u +%Y-%m-%dT%H:%M:%SZ) ---"

if [ ! -x "$REPO/.venv/bin/python" ]; then
  echo "no venv at $REPO/.venv -- run: python3 -m venv .venv && .venv/bin/pip install boto3"
  exit 1
fi

# An expired SSO token is the expected failure, not a surprise, so say which
# one it is. A generic traceback in a log nobody reads is how a monitor quietly
# stops having anything to monitor.
if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "AWS credentials are not usable. If this is an SSO profile, run:"
  echo "    aws sso login"
  exit 1
fi

"$REPO/.venv/bin/python" "$REPO/tools/traffic.py" "$@"
