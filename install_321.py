"""Install 321code from the official GitHub repository using the current Python."""
from __future__ import annotations

import subprocess
import sys

PACKAGE = "git+https://github.com/kaielk09/jenzyku.git"


def main() -> int:
    if sys.version_info < (3, 10):
        print("321code wymaga Python 3.10 lub nowszego.")
        return 1

    print("Instalowanie 321code z GitHuba...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", PACKAGE],
        check=False,
    )
    if result.returncode == 0:
        print("\nGotowe! Otworz nowe okno CMD i wpisz: 321 help")
    else:
        print("\nInstalacja nie powiodla sie. Sprawdz polaczenie z internetem i pip.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
