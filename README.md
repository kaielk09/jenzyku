# 321code

**321code** is a Polish-first, extensible programming language and command-line tool. Source files use the `.321` extension.

> Current status: early prototype (version 0.2). The interpreter supports variables, expressions, conditions, loops, functions and local imports. The command catalogue is still small; this project does **not** claim to contain 100,000 verified commands.

## Install (Python 3.10+)

From the repository directory:

```bash
python -m pip install .
321 version
321 help
321 run examples/hello.321
```

If the `321` command is not found, use `python -m code321.cli` instead.

## Language example

```321
let name = "Świecie"
let count = 0

def greet(person):
    print "Witaj, " + person

greet(name)

while count < 3:
    print count
    set count = count + 1

if count == 3:
    print "Gotowe!"
else:
    print "Jeszcze nie"
```

Run it with `321 run examples/hello.321`. More examples and syntax are documented in [docs/SYNTAX.md](docs/SYNTAX.md).

## CLI equivalents

| Familiar command | 321code command |
|---|---|
| `npm start` | `321 start` |
| `npm run build` | `321 build` |
| `npm install` | `321 install` |
| `python main.py` | `321 run main.321` |
| `clear` | `321 clear` |

These are 321code CLI commands, not automatic translations of every external tool. Project scripts are configured in `321code.json`. The `install` command is still a placeholder and does not download packages.

## Safety and current limits

Expressions use a restricted AST evaluator. The language does not execute source with Python `eval` or `exec`. Loops and function-call depth have limits. Imports are restricted to `.321` files within the project folder. Project scripts in `321code.json` launch external programs, so only run scripts from projects you trust.

## Roadmap

- [x] CLI and `.321` interpreter
- [x] Variables, expressions, conditions, loops and functions
- [x] Local module imports
- [x] Command catalogue and project scripts
- [ ] Verified package registry and real `321 install`
- [ ] Windows installer and Android/Termux package
- [ ] Expanded, reviewed command database

A useful command catalogue needs documentation, compatibility checks and tests; a large count alone does not make commands useful.

## License

MIT. See `LICENSE`.
