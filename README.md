# 321code

**321code** is a Polish-first, extensible programming language and command-line tool. Source files use the `.321` extension.

> Current status: early prototype. This repository contains the interpreter foundation and a small, curated command catalogue. It does **not** claim to contain 100,000 verified commands yet.

## Install (Python 3.10+)

From the repository directory:

```bash
python -m pip install .
```

The package installs a command named `321` on systems where the Python Scripts/bin directory is on PATH.

Check it:

```bash
321 version
321 help
321 run examples/hello.321
```

If the `321` command is not found, run it through Python:

```bash
python -m code321.cli version
python -m code321.cli run examples/hello.321
```

## Familiar commands, 321code names

| Familiar command | 321code command |
|---|---|
| `npm start` | `321 start` |
| `npm run build` | `321 build` |
| `npm install` | `321 install` |
| `python main.py` | `321 run main.321` |
| `clear` | `321 clear` |

These are 321code CLI commands, not a promise that every external tool is automatically translated. Project scripts are configured in `321code.json`.

## Example language

```321
print "Witaj w 321code!"
let name = "Świecie"
print "Witaj, " + name
```

Run it with `321 run examples/hello.321`.

## Project scripts

Create a `321code.json` file:

```json
{
  "name": "my-project",
  "scripts": {
    "start": ["python", "app.py"],
    "build": ["python", "-m", "compileall", "."]
  }
}
```

Then use `321 start` or `321 build`. Scripts are launched as argument arrays without a shell. Only run scripts from projects you trust.

## Command catalogue

The catalogue is in `code321/commands.json`. It documents commands, categories, aliases and descriptions. The first release starts with a curated set; expansion toward 100,000 entries will require deduplication, compatibility checks, documentation and tests. A large count alone does not make commands useful or safe.

## Roadmap

- [x] Initial CLI and `.321` interpreter
- [x] Command catalogue and help
- [x] Project scripts (`start`, `build`)
- [ ] Package registry with verified packages
- [ ] Windows installer and Android/Termux package
- [ ] More language features, modules and tests
- [ ] Large, reviewed command database

## License

MIT. See `LICENSE`.
