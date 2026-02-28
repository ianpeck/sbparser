# sbparser

Parses Smash Bros fantasy wrestling tournament season data from Excel spreadsheets into normalized CSVs ready for database import. Each season's Excel workbook contains fight cards organized by month, week, and brand (Brawl/Melee/Ultimate) including PPV events. The parser produces two tables:

- **`scripts/fight.py`** — **fights** — one row per fight with metadata (brand, location, PPV, championship, fight type, etc.) → `output/fight_test.csv`
- **`scripts/result.py`** — **results** — one row per fighter per fight with decision (win/loss), match result, seed, and defending champion indicator → `output/result_test.csv`

## Project Structure
```
scripts/    ← parser scripts (fight.py, result.py)
data/       ← Excel source files
lookups/    ← reference lookup tables (locations, PPVs, championships)
output/     ← generated CSVs
```

## Requirements
- Python 3.7 or higher

## Installation

### Option 1: Quick Install (Simplest)
```bash
pip install -r requirements.txt
python scripts/fight.py
python scripts/result.py
```

### Option 2: Virtual Environment (Recommended)

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/fight.py
python scripts/result.py
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python scripts/fight.py
python scripts/result.py
```

## Deactivating Virtual Environment
When you're done:
```bash
deactivate
```

## Troubleshooting

**"pip not found"**: Use `python -m pip install -r requirements.txt` instead

**"python not found"**: Try `python3` instead of `python` (Mac/Linux)

**Permission errors**: Add `--user` flag: `pip install --user -r requirements.txt`
