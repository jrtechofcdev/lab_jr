#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"

bash -n "$ROOT/jr-wifi-lab"
bash -n "$ROOT/install.sh"
"$ROOT/jr-wifi-lab" --help >/dev/null
"$ROOT/jr-wifi-lab" --version | grep -Fq '1.0.0'
python3 -m unittest discover -s "$ROOT/tests" -p 'test_*.py' -v

if command -v shellcheck >/dev/null 2>&1; then
    shellcheck "$ROOT/jr-wifi-lab" "$ROOT/install.sh" "$ROOT/tests/run.sh"
else
    printf 'shellcheck nao instalado; etapa opcional ignorada.\n'
fi

printf 'Todos os testes locais passaram.\n'
