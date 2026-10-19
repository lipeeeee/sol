#!/usr/bin/env bash
set -eu
cd -- "$(dirname -- "$0")"
for spec in *.tex; do
  latexmk -pdf -interaction=nonstopmode -halt-on-error "$spec"
  latexmk -c "$spec"
  echo "done: ${spec%.tex}.pdf"
done
