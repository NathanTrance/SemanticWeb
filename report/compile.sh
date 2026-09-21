#!/usr/bin/env bash
# compile.sh -- build the project report and verify cross-references.
# Usage: bash compile.sh [jobname]   (default jobname: main)
set -euo pipefail

cd "$(dirname "$0")"

JOB="${1:-main}"
LOG="${JOB}.log"

echo "==> Compiling ${JOB}.tex"

pdflatex -interaction=nonstopmode -halt-on-error -file-line-error "$JOB" > /dev/null

# This report uses an inline thebibliography; only run BibTeX when a
# \bibliography{...} is actually present (writes \bibdata to the .aux).
if grep -q '\\bibdata' "${JOB}.aux" 2>/dev/null; then
  echo "==> Running bibtex"
  bibtex "$JOB" > /dev/null || echo "WARNING: bibtex reported errors (see ${JOB}.blg)"
fi

pdflatex -interaction=nonstopmode -halt-on-error -file-line-error "$JOB" > /dev/null
pdflatex -interaction=nonstopmode -halt-on-error -file-line-error "$JOB" > /dev/null

echo "==> Verifying cross-references in ${LOG}"

fail=0

if grep -q 'LaTeX Warning:.*Reference.*undefined' "$LOG" || \
   grep -q 'LaTeX Warning:.*Citation.*undefined' "$LOG"; then
  echo "ERROR: undefined references and/or citations:" >&2
  grep -E 'LaTeX Warning:.*(Reference|Citation).*undefined' "$LOG" >&2
  fail=1
fi

if grep -q 'There were undefined references' "$LOG"; then
  echo "ERROR: last pass reports unresolved references" >&2
  fail=1
fi

# literal "??" in the typeset PDF (unresolved refs render as ??)
if command -v pdftotext >/dev/null 2>&1; then
  if pdftotext "${JOB}.pdf" - 2>/dev/null | grep -Eq '\?\?'; then
    echo "ERROR: found literal '??' in ${JOB}.pdf" >&2
    fail=1
  fi
fi

if [ "$fail" -ne 0 ]; then
  echo "==> Cross-reference check FAILED -- fix the refs above and re-run" >&2
  exit 1
fi

echo "==> ${JOB}.pdf built successfully; all cross-references resolved"
