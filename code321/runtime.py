"""Restricted, safe-by-default interpreter for 321code source files."""
from __future__ import annotations

import ast
import operator
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_LOOP_ITERATIONS = 10_000
MAX_CALL_DEPTH = 100
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ReturnSignal(Exception):
    def __init__(self, value: Any):
        self.value = value


@dataclass
class Function:
    parameters: list[str]
    body: list[tuple[int, str, int]]


def _expression(source: str, variables: dict[str, Any]) -> Any:
    """Evaluate only explicitly supported Python-expression AST nodes; never eval()."""
    try:
        node = ast.parse(source, mode="eval").body
    except SyntaxError as exc:
        raise ValueError(f"Niepoprawne wyrażenie: {source}") from exc

    binary = {
        ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
    }
    compare = {
        ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
        ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
    }

    def visit(item: ast.AST) -> Any:
        if isinstance(item, ast.Constant) and isinstance(item.value, (str, int, float, bool, type(None))):
            return item.value
        if isinstance(item, ast.Name):
            if item.id in variables:
                return variables[item.id]
            if item.id in {"true", "True"}:
                return True
            if item.id in {"false", "False"}:
                return False
            if item.id in {"null", "None"}:
                return None
            raise ValueError(f"Nieznana zmienna: {item.id}")
        if isinstance(item, ast.BinOp) and type(item.op) in binary:
            left, right = visit(item.left), visit(item.right)
            if isinstance(item.op, ast.Add) and (isinstance(left, str) or isinstance(right, str)):
                return str(left) + str(right)
            return binary[type(item.op)](left, right)
        if isinstance(item, ast.UnaryOp) and isinstance(item.op, (ast.Not, ast.USub, ast.UAdd)):
            value = visit(item.operand)
            return (not value) if isinstance(item.op, ast.Not) else (-value if isinstance(item.op, ast.USub) else +value)
        if isinstance(item, ast.BoolOp) and isinstance(item.op, (ast.And, ast.Or)):
            values = [visit(v) for v in item.values]
            return all(values) if isinstance(item.op, ast.And) else any(values)
        if isinstance(item, ast.Compare):
            left = visit(item.left)
            for op, comparator in zip(item.ops, item.comparators):
                right = visit(comparator)
                if type(op) not in compare or not compare[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(item, ast.Call) and isinstance(item.func, ast.Name):
            args = [visit(arg) for arg in item.args]
            if item.func.id == "str" and len(args) == 1:
                return str(args[0])
            if item.func.id == "int" and len(args) == 1:
                return int(args[0])
            if item.func.id == "range" and 1 <= len(args) <= 3 and all(isinstance(x, int) for x in args):
                return range(*args)
            raise ValueError(f"Niedozwolone wywołanie funkcji w wyrażeniu: {item.func.id}")
        raise ValueError(f"Niedozwolony element wyrażenia: {type(item).__name__}")

    return visit(node)


class Interpreter:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()
        self.variables: dict[str, Any] = {}
        self.functions: dict[str, Function] = {}
        self.call_depth = 0
        self.import_stack: set[Path] = set()

    def _block(self, lines: list[tuple[int, str, int]], index: int, indent: int):
        body = []
        while index < len(lines) and lines[index][0] > indent:
            current_indent = lines[index][0]
            if current_indent != indent + 4:
                raise ValueError(f"Nieprawidłowe wcięcie w linii {lines[index][2]} (użyj 4 spacji)")
            body.append(lines[index])
            index += 1
        return body, index

    def _execute(self, lines: list[tuple[int, str, int]]) -> None:
        i = 0
        while i < len(lines):
            indent, line, number = lines[i]
            if indent != 0:
                raise ValueError(f"Nieoczekiwane wcięcie w linii {number}")

            if line.startswith("if ") and line.endswith(":"):
                yes, after = self._block(lines, i + 1, indent)
                no = []
                if after < len(lines) and lines[after][0] == 0 and lines[after][1] == "else:":
                    no, after = self._block(lines, after + 1, 0)
                condition = bool(_expression(line[3:-1], self.variables))
                self._execute(yes if condition else no)
                i = after
                continue

            if line.startswith("while ") and line.endswith(":"):
                body, after = self._block(lines, i + 1, indent)
                count = 0
                while _expression(line[6:-1], self.variables):
                    count += 1
                    if count > MAX_LOOP_ITERATIONS:
                        raise ValueError(f"Przekroczono limit {MAX_LOOP_ITERATIONS} powtórzeń pętli")
                    self._execute(body)
                i = after
                continue

            match = re.fullmatch(r"for\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\s+range\((.*)\):", line)
            if match:
                body, after = self._block(lines, i + 1, indent)
                values = _expression("range(" + match.group(2) + ")", self.variables)
                if len(values) > MAX_LOOP_ITERATIONS:
                    raise ValueError(f"Pętla przekracza limit {MAX_LOOP_ITERATIONS} powtórzeń")
                for value in values:
                    self.variables[match.group(1)] = value
                    self._execute(body)
                i = after
                continue

            match = re.fullmatch(r"def\s+([A-Za-z_][A-Za-z0-9_]*)\(([^()]*)\):", line)
            if match:
                params = [p.strip() for p in match.group(2).split(",") if p.strip()]
                if any(not NAME.fullmatch(p) for p in params) or len(params) != len(set(params)):
                    raise ValueError("Niepoprawne parametry funkcji")
                body, after = self._block(lines, i + 1, indent)
                if not body:
                    raise ValueError("Funkcja musi mieć treść")
                self.functions[match.group(1)] = Function(params, body)
                i = after
                continue

            if line.startswith("print "):
                print(_expression(line[6:], self.variables))
            elif line.startswith("let ") or line.startswith("set "):
                match = re.fullmatch(r"(?:let|set)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)", line)
                if not match:
                    raise ValueError("Użycie: let nazwa = wyrażenie")
                self.variables[match.group(1)] = _expression(match.group(2), self.variables)
            elif line.startswith("return"):
                value = line[6:].strip()
                raise ReturnSignal(_expression(value, self.variables) if value else None)
            elif line.startswith("import "):
                target = line[7:].strip().strip('"').strip("'")
                self.import_file(target)
            else:
                call = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\((.*)\)", line)
                if not call or call.group(1) not in self.functions:
                    raise ValueError(f"Nieznana instrukcja lub funkcja: {line}")
                self.call(call.group(1), call.group(2))
            i += 1

    def call(self, name: str, arguments: str):
        function = self.functions[name]
        values = [] if not arguments.strip() else [_expression(x.strip(), self.variables) for x in arguments.split(",")]
        if len(values) != len(function.parameters):
            raise ValueError(f"Funkcja {name} oczekuje {len(function.parameters)} argumentów")
        if self.call_depth >= MAX_CALL_DEPTH:
            raise ValueError("Przekroczono limit zagnieżdżenia funkcji")
        old = self.variables.copy()
        self.variables.update(zip(function.parameters, values))
        self.call_depth += 1
        try:
            self._execute(function.body)
        except ReturnSignal as result:
            return result.value
        finally:
            self.call_depth -= 1
            self.variables = old
        return None

    def import_file(self, filename: str):
        candidate = (self.base_dir / filename).resolve()
        if candidate.suffix != ".321" or self.base_dir not in candidate.parents:
            raise ValueError("Import jest dozwolony tylko dla plików .321 wewnątrz folderu projektu")
        if candidate in self.import_stack:
            raise ValueError(f"Wykryto zapętlony import: {filename}")
        if not candidate.is_file():
            raise ValueError(f"Nie znaleziono modułu: {filename}")
        self.import_stack.add(candidate)
        try:
            self._execute(self._parse(candidate))
        finally:
            self.import_stack.remove(candidate)

    @staticmethod
    def _parse(path: Path):
        parsed = []
        for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            leading = len(raw) - len(raw.lstrip(" "))
            if "\t" in raw[:leading]:
                raise ValueError(f"Tabulatory są niedozwolone (linia {number})")
            parsed.append((leading, raw.strip(), number))
        return parsed

    def run(self, path: Path):
        resolved = path.resolve()
        self.base_dir = resolved.parent
        self.import_stack.add(resolved)
        try:
            self._execute(self._parse(resolved))
        finally:
            self.import_stack.discard(resolved)


def run_file(path: Path) -> int:
    if not path.is_file():
        print(f"Nie znaleziono pliku: {path}", file=sys.stderr)
        return 1
    try:
        Interpreter(path.parent).run(path)
    except (OSError, UnicodeError, ValueError, TypeError, ZeroDivisionError, ReturnSignal) as exc:
        print(f"{path}: {exc}", file=sys.stderr)
        return 1
    return 0
