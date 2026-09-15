#!/usr/bin/env bash
# Runs the full suite and regenerates report.html, a single self-contained
# file you can open directly in a browser.
set -uo pipefail
cd "$(dirname "$0")"

# A handful of tests are *expected* to fail against known, tracked product
# defects (see BUGS.md) - that's the point of this suite, not a script bug.
# Capture the exit code instead of letting `set -e` cut the run short before
# the report gets generated.
python3 -m pytest "$@"
pytest_exit_code=$?

echo "Report: report.html"
exit "$pytest_exit_code"
