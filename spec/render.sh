#!/usr/bin/env bash
set -eu
cd -- "$(dirname -- "$0")"
latexmk -pdf -interaction=nonstopmode -halt-on-error dataset.tex
latexmk -c dataset.tex
echo "done: dataset.pdf"
