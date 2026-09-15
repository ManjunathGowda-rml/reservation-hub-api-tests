#!/usr/bin/env bash
# Runs the full suite and (re)generates both reports:
#   report.html        - single self-contained file, open directly in a browser
#   allure-report/      - richer, navigable report; needs `allure open allure-report`
#                          (or any local web server) because of browser XHR
#                          restrictions on file:// pages - see README.
set -uo pipefail
cd "$(dirname "$0")"

rm -rf allure-results allure-report

# A handful of tests are *expected* to fail against known, tracked product
# defects (see BUGS.md) - that's the point of this suite, not a script bug.
# Capture the exit code instead of letting `set -e` cut the run short before
# the reports get generated.
pytest "$@"
pytest_exit_code=$?

if command -v allure >/dev/null 2>&1; then
  allure generate allure-results --clean -o allure-report
  echo "Allure report generated at allure-report/ - view it with: allure open allure-report"
else
  echo "allure CLI not found - skipping Allure HTML generation (raw results are in allure-results/)"
fi

echo "Self-contained report: report.html"
exit "$pytest_exit_code"
