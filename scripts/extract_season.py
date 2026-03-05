"""Extract a season from the master Smash Bros spreadsheet into parser-ready format.

The master file (Smash Bros Season.xlsx) stores season data in a horizontal
layout — all 12 months are placed side by side in wide column blocks. The
parsers (fight.py, result.py) expect a vertical layout — months stacked top
to bottom in 6 columns. This script converts from horizontal to vertical.

Usage:
    1. Set season_sheet and excel_file in config.yaml
    2. Run: python scripts/extract_season.py
    3. The extracted file appears in data/ ready for fight.py and result.py
"""

from pathlib import Path

import pandas as pd
import yaml

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
with open(BASE_DIR / "config.yaml") as f:
    _config = yaml.safe_load(f)

MASTER_FILE = BASE_DIR / "input" / _config["master_file"]
OUTPUT_FILE = BASE_DIR / "input" / _config["excel_file"]
SEASON_SHEET = _config["season_sheet"]

# The parsers expect exactly 6 columns of data per row
OUTPUT_COLUMNS = 6


def find_month_columns(df):
    """Find the column index of each 'Month N' header in row 0.

    Returns:
        list[int]: Column indices where month headers appear, in order.
    """
    month_cols = []
    for j in range(df.shape[1]):
        val = df.iloc[0, j]
        if pd.notna(val) and "Month" in str(val):
            month_cols.append(j)
    return month_cols


def extract_month_block(df, start_col, end_col):
    """Extract a single month's data as a 6-column block.

    Takes columns [start_col, start_col+5] from the source and trims
    trailing all-NaN rows. Stops extraction if draft/swap data is encountered.

    Args:
        df: The full horizontal DataFrame.
        start_col: Column index where this month starts.
        end_col: Column index where the next month starts (used as upper bound).

    Returns:
        pd.DataFrame: The month block with 6 columns, trailing blanks removed.
    """
    # Take 6 columns starting from the month header column
    col_end = min(start_col + OUTPUT_COLUMNS, end_col, df.shape[1])
    block = df.iloc[:, start_col:col_end].copy()

    # Pad to 6 columns if the block is narrower (e.g. last month)
    while block.shape[1] < OUTPUT_COLUMNS:
        block[block.shape[1]] = float("nan")

    # Normalize column names to 0-5
    block.columns = range(OUTPUT_COLUMNS)

    # Trim trailing all-NaN rows, but stop at draft/swap data
    last_data_row = 0
    draft_keywords = ["draft", "swap", "trade"]

    for i in range(len(block)):
        # Check if any cell in this row contains draft/swap keywords
        row_text = [str(cell).lower() for cell in block.iloc[i]]
        if any(keyword in text for text in row_text for keyword in draft_keywords):
            # Stop extraction here - don't include this row or anything after
            break

        if block.iloc[i].notna().any():
            last_data_row = i

    block = block.iloc[: last_data_row + 1]

    return block


def extract_season(df):
    """Convert a horizontal season tab into vertical parser-ready format.

    Scans row 0 for 'Month N' headers, extracts each month's 6-column block,
    and stacks them vertically with a leading blank row.

    Returns:
        pd.DataFrame: Vertically stacked season data with 6 columns.
    """
    month_cols = find_month_columns(df)

    if not month_cols:
        raise ValueError(f"No 'Month N' headers found in row 0 of sheet '{SEASON_SHEET}'")

    blocks = []

    # Leading blank row (matches reference FullSeason5.xlsx format)
    blank_row = pd.DataFrame([[float("nan")] * OUTPUT_COLUMNS], columns=range(OUTPUT_COLUMNS))
    blocks.append(blank_row)

    for idx, start_col in enumerate(month_cols):
        # End column is the start of the next month, or end of data
        end_col = month_cols[idx + 1] if idx + 1 < len(month_cols) else df.shape[1]

        block = extract_month_block(df, start_col, end_col)
        blocks.append(block)

    result = pd.concat(blocks, ignore_index=True)
    return result


def main():
    """Entry point: read master file, extract season, write output."""
    print(f"Reading '{SEASON_SHEET}' from {MASTER_FILE.name}...")
    df = pd.read_excel(MASTER_FILE, sheet_name=SEASON_SHEET, header=None)

    result = extract_season(df)
    print(f"Extracted {len(result)} rows x {result.shape[1]} columns")

    result.to_excel(OUTPUT_FILE, sheet_name="Sheet1", index=False, header=False)
    print(f"Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
