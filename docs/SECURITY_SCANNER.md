# 321 Security Scanner

321 Security Scanner is a defensive, static-first inspection tool built into the 321code CLI. It does not execute files, install software, exploit websites, or upload scanned data to third-party services.

## Commands

Choose a folder once:

```bat
321 cd "C:\Users\filip\Desktop\MojProgram"
```

The selected folder is stored in the current user's application configuration, so it remains selected after closing CMD or opening a new terminal window.

Scan the selected folder:

```bat
321 sprawdź
```

Inspect a public website:

```bat
321 sprawdź internet https://replit.com
```

The unaccented spelling `321 sprawdz` is also accepted.

## What is inspected?

### Local files

The scanner walks through the selected folder and checks bounded file contents and printable strings. It does not rely only on file extensions, so source files, configuration files and binaries can all contain indicators. It looks for known service/API hostnames (including OpenAI, TostHost, Hugging Face, Discord and GitHub), selected suspicious code patterns and possible secret/key patterns. Secret values are never printed.

Limits: 20 seconds, 5,000 files, and 8 MiB per file. Large files and unreadable files are skipped. If the time or file-count limit is reached, the report is marked incomplete.

### Websites

Website mode makes a single bounded HTTP(S) request. It reports the response status, final URL, HTTPS usage, selected security headers, external domains, and API/service identifiers present in the returned response. It does not crawl the whole site, execute JavaScript, test authentication, or perform penetration testing. Requests to localhost and private/non-public IP ranges are blocked, including checked redirects.

## Understanding the report

- **Detected API/service** means a known hostname or identifier appeared in inspected content. It does not prove that the program actively calls that service.
- **Suspicious indicator** is a heuristic match. Legitimate software can contain the same pattern.
- **No indicators** does not mean a file or website is guaranteed safe.
- **High/medium/low** are heuristic priorities, not confirmed malware classifications.

For stronger verification, use an up-to-date endpoint security product such as Microsoft Defender. This scanner is an additional inspection aid, not a replacement for antivirus software.

## Privacy and safety

- Files are inspected locally and are not uploaded to VirusTotal or any other scanning service.
- Never run a suspicious file just to see what it does.
- Treat API keys and tokens as secrets. The scanner only reports the file containing a possible secret pattern; it does not display the value.
- Only scan websites you are allowed to inspect. The website mode performs a basic public-page review, not a security audit.

## Google Colab

The core module uses the Python standard library and can be imported in a CPU-only Colab notebook. Colab can test the static analysis and public website request, but it cannot verify Windows CMD integration or Windows Defender integration.
