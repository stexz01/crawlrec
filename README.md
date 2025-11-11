# CrawlRec

CrawlRec is a **humanized Playwright-based recorder and extractor** that allows you to record element selectors interactively and later re-run automated extractions.  
It includes stealth behavior, randomized user agents, and graceful shutdown handling to avoid detection and prevent stuck sessions.

<img src="https://github.com/user-attachments/assets/e25e834b-a524-4542-9d7a-b12e95317486" width="1000" />

<p align="center">
  <img src="demos/crawlrec.gif" width="1000" />
</p>

---

## Features

- **Interactive Recorder** — Capture element selectors directly by clicking within a live browser session.  
- **Stealth Mode** — Implements multiple anti-bot evasion techniques to reduce automation fingerprints.  
- **Humanized Behavior** — Simulates realistic browsing actions with randomized user agents, mouse movement, and interaction delays.  
- **Reusable Templates** — Saves all recorded actions as structured JSON for replay or integration with other tools.  
---

## Installation

```bash
pip install git+https://github.com/stexz01/crawlrec.git
```

CrawlRec requires:
- Playwright browsers (installed via `playwright install`)

---

## Record Mode

Interactively record selectors from any website.

```bash
crawlrec record https://example.com -o example.json
```

During recording:
- Click elements directly in the opened browser to capture them.
- Choose what to extract (`text` or `href`) from the prompt.
- Use `Ctrl + C` or select **“Exit & Save”** to stop and save your session.

---

## Extract Mode

Run a saved JSON template to extract data from a page.

```bash
crawlrec extract -t crawls/example.json
```

You can override the URL if needed:

```bash
crawlrec extract -t crawls/template.json -u https://newpage.com
```

---

## Example Output

A recording session produces a JSON file similar to:

```json
{
  "url": "https://example.com",
  "actions": [
    {
      "selector": "a[href='/about']",
      "extract": "href",
      "text": "About Us"
    },
    {
      "selector": "h1.main-title",
      "extract": "text",
      "text": "Welcome to Example"
    }
  ]
}
```

---

## Command-Line Reference

```bash
usage: crawlrec.py [-h] {record,extract} ...

CrawlRec — Humanized Playwright Recorder & Extractor

positional arguments:
  {record,extract}
    record      Record selectors interactively
    extract     Extract data from saved JSON

options:
  -h, --help    Show this help message and exit
```

---

## Author

**stexz01**  
GitHub: [@stexz01](https://github.com/stexz01)

---

## Contributing

Pull requests and feature improvements are welcome.  
If you encounter bugs or have feature suggestions, please open an issue on the GitHub repository.

---

Thank You (:
