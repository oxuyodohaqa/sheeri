# SheerID CLI (PC / Command Prompt)

Run the SheerID verification flow directly from a PC command prompt (no Docker, no web server). The CLI uses the same HTML template and document generation process as the original project.

## Requirements
- Python 3.9+ on your machine
- Google Chrome/Chromium for Playwright screenshots
- Network access to SheerID APIs

Install dependencies:
```bash
python -m pip install -r requirements.txt
python -m playwright install chromium  # for PNG screenshot support
```

## Usage
You can paste a full SheerID link or a raw `verificationId`.

### Quick run (non-interactive)
```bash
python run_cli.py --url "https://my.sheerid.com/verify/68d47554aa292d20b9bec8f7?verificationId=YOUR_ID" --school-id 3995910
```

### Guided prompts
If you omit arguments you will be asked for them interactively:
```bash
python run_cli.py
```
The script will:
1. Ask for the verification link/ID.
2. Show the school list from `config.py` and let you pick an ID.
3. Generate the PDF/PNG documents and submit them to SheerID.

### Listing schools
Use the original helper in `sheerid_verifier.py`:
```bash
python sheerid_verifier.py --list-schools
```

## Files
- `run_cli.py` – small command-line wrapper for PC usage.
- `sheerid_verifier.py` – core logic (unchanged, still usable directly).
- `config.py` – school list and program configuration.
- `card-temp.html` – HTML template used for PDF/PNG generation.

## Notes
- The PNG step requires Playwright with Chromium. If you only need PDF upload, install requirements and skip `playwright install chromium`.
- No Docker or web server is needed; everything runs from the local command prompt.
