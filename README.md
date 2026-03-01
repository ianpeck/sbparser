# sbparser

Parses Smash Bros fantasy wrestling tournament season data from Excel spreadsheets into normalized CSVs ready for database import. Each season's Excel workbook contains fight cards organized by month, week, and brand (Brawl/Melee/Ultimate) including PPV events. The parser produces two tables:

- **`scripts/extract_season.py`** — extracts a season tab from the master spreadsheet into parser-ready vertical format
- **`scripts/fight.py`** — **fights** — one row per fight with metadata (brand, location, PPV, championship, fight type, etc.) → `output/season_{season}_fight.csv`
- **`scripts/result.py`** — **results** — one row per fighter per fight with decision (win/loss), match result, seed, and defending champion indicator → `output/season_{season}_result.csv`

## Configuration

All season-specific settings live in **`config.yaml`**. To parse a new season, update this file and drop the Excel workbook into `input/` — no code changes needed.

```yaml
season: 5
fight_id_start: 1911
result_id_start: 4324
excel_file: FullSeason5.xlsx
master_file: "Smash Bros Season.xlsx"
season_sheet: "Season 5"
```

## Project Structure
```
config.yaml ← season-specific settings (season, IDs, filenames)
scripts/    ← extract_season.py, fight.py, result.py
input/      ← Excel source files
lookups/    ← reference lookup tables (brands, fight types, championships, locations, PPVs)
output/     ← generated CSVs (season_5_fight.csv, season_5_result.csv)
```

## Lookup CSVs

The `lookups/` directory contains reference data loaded at runtime. All brands, fight types, and championships are stored in CSV files — no hardcoded constants in the Python scripts.

- **Brand.csv** — Brand IDs (Brawl, Melee, Ultimate)
- **FightType.csv** — Fight type IDs (Three Stock, Hardcore, Tag, Brawlmania, etc.)
- **Championship.csv** — Championship IDs (Melee, Brawl, Ultimate, Smash Bros., etc.)
- **Location_ID.csv** — Location IDs and metadata
- **PPV.csv** — PPV IDs and descriptions

## Output Files

Generated CSVs are named dynamically based on the season in `config.yaml`:
- `output/season_5_fight.csv` (for season 5)
- `output/season_5_result.csv` (for season 5)

When you update `season: 6` in the config, output files will automatically be named `season_6_fight.csv` and `season_6_result.csv`.

## Requirements
- Python 3.7 or higher

## Installation

### Option 1: Quick Install (Simplest)
```bash
pip install -r requirements.txt
python scripts/extract_season.py  # extract from master spreadsheet
python scripts/fight.py
python scripts/result.py
```

### Option 2: Virtual Environment (Recommended)

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/extract_season.py  # extract from master spreadsheet
python scripts/fight.py
python scripts/result.py
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python scripts/extract_season.py  # extract from master spreadsheet
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
