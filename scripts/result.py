"""Parse fighter results from a Smash Bros tournament Excel spreadsheet.

Reads the Excel file specified in config.yaml and extracts one row per fighter
per fight, including decision (win/loss), match result value, seed, and
defending indicator. Outputs result_test.csv.
"""

import re
from pathlib import Path

import pandas as pd
import yaml

# ---------------------------------------------------------------------------
# Config — season-specific values loaded from config.yaml
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
with open(BASE_DIR / "config.yaml") as f:
    _config = yaml.safe_load(f)

SEASON = _config["season"]
RESULT_ID_START = _config["result_id_start"]
FIGHT_ID_START = _config["fight_id_start"]

# Brand names that can appear in fighter columns but are not actual fighters
BRAND_NAMES = {"Brawl", "Melee", "Ultimate"}

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

EXCEL_PATH = BASE_DIR / "input" / _config["excel_file"]
OUTPUT_CSV = BASE_DIR / "output" / f"season_{SEASON}_result.csv"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def parse_fighters_from_row(row, df, index, fight_id, result_id):
    """Extract all fighter results from a single fighter row.

    Fighter rows have a numeric seed in column 1. Fighters appear in
    columns 2+ as strings. Each fighter's match result (stocks remaining) is in
    the cell directly below their name.

    Args:
        row: The current DataFrame row.
        df: The full DataFrame (needed to read the result row below).
        index: Row index in the DataFrame.
        fight_id: Current fight ID to associate results with.
        result_id: Next result ID to assign (incremented per fighter).

    Returns:
        tuple: (list_of_result_dicts, updated_result_id)
    """
    results = []

    # Fighters can only appear past column 2 (columns 0-1 are metadata/seed)
    fighters = row.iloc[2:][row.iloc[2:].apply(lambda x: isinstance(x, str))].tolist()

    for fighter in fighters:
        if fighter in BRAND_NAMES:
            continue  # skip brand names that leak into fighter columns

        # Clean fighter name — remove win marker, power level tag, defending tag, dots
        fighter_name = (
            fighter.replace("- W", "")
            .replace("(PL)", "")
            .replace("(Defending)", "")
            .replace(".", "")
            .strip()
        )

        decision = "w" if "- W" in fighter else "l"

        # Find the column index of this fighter to read the result below
        fighter_index = row[row == fighter].index[0]
        fighter_col_index = df.columns.get_loc(fighter_index)

        # --- Seed extraction ---
        # Seeds appear in "vs." rows (e.g. "1 vs. 4") where position
        # maps to column: col 2 → first seed, col 3 → seed after "vs."
        seed = None
        if row.astype(str).str.contains("vs.").any():
            seed_string = df.iloc[index, 0]
            if fighter_col_index == 2:
                seed = seed_string.split()[0]  # first seed
            elif fighter_col_index == 3:
                seed = seed_string.split()[2]  # seed after "vs."

        # --- Defending indicator ---
        # Determines if a fighter is the defending champion in this match
        defending = None
        # If the row below (col 0) contains "forfeited title", the title was vacated — no defender
        next_col0 = str(df.iloc[index + 1, 0]) if index + 1 < len(df) else ""
        title_forfeited = "forfeited" in next_col0.lower() and "title" in next_col0.lower()
        if title_forfeited:
            defending = None
        elif pd.notna(row.iloc[0]) and re.findall(
            r"^(?!.*\b(spot|added)\b).* championship$", str(row.iloc[0]).lower().strip()
        ):
            if "vs." in str(row.iloc[0]).lower() and "(Defending)" not in fighter:
                # Tournament/scramble match — only explicitly tagged defenders count
                defending = None
            elif fighter_col_index == 2:
                # First fighter column is the defending champion
                defending = "Y"
            elif fighter_col_index == 3 and str(row.iloc[0]).lower() == "unified tag team championship":
                # Tag partner of the defending champion also counts
                defending = "Y"
        elif "(Defending)" in fighter:
            # Explicit defending tag (used in scrambles and tournaments)
            defending = "Y"

        # Match result is in the cell directly below the fighter name
        if index + 1 < len(df):
            # Strip "HP" suffix from result values (e.g. "3HP" → "3")
            value_below = str(df.iloc[index + 1, fighter_col_index]).replace("HP", "").strip()
            results.append({
                "Result_ID": result_id,
                "Fighter_Name": fighter_name,
                "Fight_ID": fight_id,
                "Decision": decision,
                "Match_Result": value_below,
                "Seed": seed,
                "DefendingIndicator": defending,
            })
            result_id += 1

    return results, result_id


def parse_results(df):
    """Walk every row of the spreadsheet and build the results table.

    Returns:
        list[dict]: One dict per fighter-result with all columns.
    """
    all_results = []
    fight_counter = FIGHT_ID_START - 1  # pre-incremented on first fight, must match fight.py
    result_id = RESULT_ID_START

    for index, row in df.iterrows():
        # Increment fight ID each time a "- W" row is encountered
        if row.astype(str).str.contains("- W").any():
            fight_counter += 1

        # Fighter rows have a numeric seed in column 1
        if str(row.iloc[1]).isdigit():
            new_results, result_id = parse_fighters_from_row(
                row, df, index, fight_counter, result_id
            )
            all_results.extend(new_results)

    return all_results


def main():
    """Entry point: load data, parse results, and write output CSV."""
    df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1")
    results = parse_results(df)
    results_df = pd.DataFrame(results)

    # Convert numeric columns to integers (using nullable Int64 to handle NaN)
    int_columns = ["Result_ID", "Fight_ID"]
    for col in int_columns:
        if col in results_df.columns:
            results_df[col] = results_df[col].astype("Int64")

    # Seed and Match_Result may have non-numeric values, so handle separately
    if "Seed" in results_df.columns:
        results_df["Seed"] = pd.to_numeric(results_df["Seed"], errors="coerce").astype("Int64")

    results_df.to_csv(OUTPUT_CSV, index=False)


if __name__ == "__main__":
    main()
