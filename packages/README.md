# 321code package registry

This repository hosts the default package index at packages/index.json.

## Package archive format

Each package is a ZIP archive with a package.json at its root and one or more .321 source files.

Example manifest:

```json
{
  "name": "hello321",
  "version": "1.0.0",
  "description": "Example 321code package",
  "dependencies": {}
}
```

The registry entry contains the HTTPS archive URL, its SHA-256 digest, and optional exact-version dependencies:

```json
{
  "schema_version": 1,
  "packages": {
    "hello321": {
      "version": "1.0.0",
      "url": "https://example.org/hello321-1.0.0.zip",
      "sha256": "64-character-hex-digest",
      "dependencies": {}
    }
  }
}
```

Only publish packages you have permission to distribute. The installer verifies SHA-256 and rejects unsafe archive paths, symbolic links, oversized archives, and packages without a manifest or .321 source file.

## Local workflow

1. Create a package folder with package.json and .321 files.
2. Build it with 321 packages pack path/to/package.
3. Install the resulting ZIP in a project with 321 install path/to/package.zip.
4. Import a module using import "package-name/module.321".

The public index starts empty; a package becomes installable by name only after a maintainer adds a verified archive entry to packages/index.json.
