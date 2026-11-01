"""Small, deliberately restricted interpreter for .321 source files."""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


def _value(expression: str, variables: dict[str, str]) -> str:
    expression = expression.strip()
    if expression.startswith('"') and expression.endswith('"'):
        return ast.literal_eval(expression)
    if expression.startswith("'") and expression.endswith("'"):
        return ast.literal_eval(expression)
    if expression in variables:
        return variables[expression]
    # Support simple string concatenation without eval().
    parts = re.split(r'\s*\+\s*', expression)
    if len(parts) > 1:
        return "".join(_value(part, variables) for part in parts)
    return expression


def run_file(path: Path) -> int:
    if not path.is_file():
        print(f"Nie znaleziono pliku: {path}", file=sys.stderr)
        return 1

    variables: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("print "):
                print(_value(line[6:], variables))
            elif line.startswith("let "):
                match = re.fullmatch(r"let\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)", line)
                if not match:
                    raise ValueError("Użycie: let nazwa = wartość")
                variables[match.group(1)] = _value(match.group(2), variables)
            else:
                raise ValueError(f"Nieznana instrukcja: {line}")
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"{path}:{number if 'number' in locals() else 1}: {exc}", file=sys.stderr)
        return 1
    return 0
