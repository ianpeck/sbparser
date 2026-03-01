"""Parse fight metadata from a Smash Bros tournament Excel spreadsheet.

Reads the Excel file specified in config.yaml and extracts one row per fight
with brand, location, PPV, championship, fight type, season, month, week, and
contender indicator. Outputs fight_test.csv.
"""

import math
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
FIGHT_ID_START = _config["fight_id_start"]

# Lookup dictionaries (loaded from CSVs at runtime)
BRANDS = {}
FIGHT_TYPES = {}
CHAMPIONSHIP_NAMES = []

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

EXCEL_PATH = BASE_DIR / "input" / _config["excel_file"]
LOCATION_CSV = BASE_DIR / "lookups" / "Location_ID.csv"
PPV_CSV = BASE_DIR / "lookups" / "PPV.csv"
BRAND_CSV = BASE_DIR / "lookups" / "Brand.csv"
FIGHT_TYPE_CSV = BASE_DIR / "lookups" / "FightType.csv"
CHAMPIONSHIP_CSV = BASE_DIR / "lookups" / "Championship.csv"
OUTPUT_CSV = BASE_DIR / "output" / f"season_{SEASON}_fight.csv"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def load_reference_data():
    """Load all lookup tables from CSV files.

    Populates global BRANDS, FIGHT_TYPES, and CHAMPIONSHIP_NAMES dictionaries.

    Returns:
        tuple: (location_dict, ppv_dict) mapping lowercase names to IDs.
    """
    global BRANDS, FIGHT_TYPES, CHAMPIONSHIP_NAMES

    df_location = pd.read_csv(LOCATION_CSV)
    location_dict = dict(
        zip(df_location["Location_Name"].str.lower(), df_location["Location_ID"])
    )

    df_ppv = pd.read_csv(PPV_CSV)
    ppv_dict = dict(
        zip(df_ppv["PPV_Name"].str.lower(), df_ppv["PPV_ID"])
    )

    df_brands = pd.read_csv(BRAND_CSV)
    BRANDS = dict(zip(df_brands["Brand_Name"], df_brands["Brand_ID"]))

    df_fight_types = pd.read_csv(FIGHT_TYPE_CSV)
    FIGHT_TYPES = dict(zip(df_fight_types["FightType_Name"], df_fight_types["FightType_ID"]))

    df_championships = pd.read_csv(CHAMPIONSHIP_CSV)
    CHAMPIONSHIP_NAMES = df_championships["Championship_Name"].tolist()

    return location_dict, ppv_dict


def parse_brand_or_ppv(row):
    """Detect whether a row is a brand or PPV header.

    Brand/PPV headers have a value in column 1 but not in column 0, and the
    value is not a bare number (which would be a seed).

    Returns:
        tuple: (brand_id_or_None, ppv_name_or_None, location_string)
    """
    if pd.notna(row[1]) and pd.isna(row[0]) and not str(row[1]).isdigit():
        label = str(row[1]).strip()
        brand = BRANDS.get(label)
        ppv = label if label not in BRANDS else None
        location = str(row[2]).strip()
        return brand, ppv, location
    return None, None, None


def parse_championship(row):
    """Detect a championship match header row.

    Matches rows like "Brawl Championship" but excludes rows containing
    "spot" or "added" (those are contender matches, not title matches).
    For tournament-style championship rows with "vs.", extract just the
    championship name portion.

    Returns:
        str or None: Championship name if detected, else None.
    """
    if pd.notna(row[0]) and re.findall(
        r"^(?!.*\b(spot|added)\b).* championship$", str(row[0]).lower().strip()
    ):
        if "vs." in str(row[0]).lower().strip():
            # e.g. "1 vs. 2 Brawl Championship" → "Brawl Championship"
            parts = str(row[0]).split()
            return parts[4] + " " + parts[5]
        return str(row[0]).strip()
    return None


def parse_contender(row):
    """Detect a #1 contender or "spot in <championship>" match.

    Returns:
        str or None: The contender description if detected, else None.
    """
    if pd.notna(row[0]):
        text_lower = str(row[0]).lower()
        # "#1 Contender <name>" pattern
        if re.findall(r"^#1 contender \w+$", text_lower):
            return row[0]
        # "Spot in <championship>" pattern
        champ_pattern = "|".join(re.escape(c.lower()) for c in CHAMPIONSHIP_NAMES)
        if re.findall(rf"^spot in ({champ_pattern})$", text_lower):
            return row[0]
    return None


def determine_fight_type(row, next_row, current_ppv):
    """Classify the fight type based on the current and next row text.

    The classification chain is order-dependent — earlier matches take
    priority over later ones (e.g. Tag is checked before Hardcore).

    Args:
        row: Current DataFrame row.
        next_row: The row immediately below (or None if at end).
        current_ppv: Name of the current PPV context, if any.

    Returns:
        int: Fight type ID from FIGHT_TYPES lookup.
    """
    if pd.isna(row[0]):
        return FIGHT_TYPES["Three Stock"]

    text = str(row[0])
    text_lower = text.lower().strip()
    next_text_lower = str(next_row[0]).lower().strip() if next_row is not None else ""

    # Tag match — checked first because tag matches can overlap with other types
    if "Tag" in text:
        return FIGHT_TYPES["Tag"]

    # Coin match — indicated by "coin match..." on the row below
    if re.match(r"^coin match.*", next_text_lower):
        return FIGHT_TYPES["Coin"]

    # Brawlmania Hardcore — hardcore during Brawlmania is its own type
    if "hardcore" in text_lower and current_ppv == "Brawlmania":
        return FIGHT_TYPES["Brawlmania Hardcore"]

    # Hardcore — either in this row's text or "hardcore match" on the next row
    if "hardcore" in text_lower or "hardcore match" in next_text_lower:
        return FIGHT_TYPES["Hardcore"]

    # Special championship / contender / spot-in on a row with a following row
    if text_lower in [
        "special championship", "#1 contender special", "spot in special"
    ] and pd.notna(next_row[0]) if next_row is not None else False:
        return FIGHT_TYPES["Special"]

    # Championship Scramble PPV — any "vs" row during this PPV
    if current_ppv == "Championship Scramble" and "vs" in text_lower:
        return FIGHT_TYPES["Championship Scramble"]

    # Brawlmania PPV — any remaining fight during Brawlmania
    if current_ppv == "Brawlmania":
        return FIGHT_TYPES["Brawlmania"]

    # Royal Rumble
    if text.strip() == "Royal Rumble":
        return FIGHT_TYPES["Royal Rumble"]

    # Pokeball Match
    if text.strip() == "Pokeball Match":
        return FIGHT_TYPES["Pokeball"]

    # Money in the Bank ladder matches
    if text.strip().lower() in ["mitb melee", "mitb ultimate", "mitb brawl"]:
        return FIGHT_TYPES["Money in the Bank"]

    # Final Destination Tournament PPV
    if current_ppv == "Final Destination Tournament":
        return FIGHT_TYPES["Final Destination"]

    # Cash-in — indicated by "cash" on the row below
    if "cash" in next_text_lower:
        return FIGHT_TYPES["Cash In"]

    # Handicap match — indicated by "handicap match" on the row below
    if next_text_lower == "handicap match":
        return FIGHT_TYPES["Handicap"]

    # Smash Series match
    if text_lower == "smash series match":
        return FIGHT_TYPES["Smash Series"]

    # Default: standard 3-stock match
    return FIGHT_TYPES["Three Stock"]


def parse_month(row, current_month):
    """Extract the month number from a "Month N" header row.

    Returns:
        str: Updated month value (unchanged if this row is not a month header).
    """
    if pd.notna(row[0]) and "Month" in str(row[0]):
        return str(row[0]).replace("Month ", "")
    return current_month


def update_week(row, week_change_counter):
    """Track week progression within a month.

    Weeks are separated by fully-blank rows in the spreadsheet. Every two
    blank rows advance the week counter by one (because blank rows appear
    between brands within the same week).

    Returns:
        tuple: (week_number, updated_counter)
    """
    # Reset counter when a new month starts
    if pd.notna(row[0]) and "Month" in str(row[0]):
        week_change_counter = 0

    # A fully-blank row signals a show boundary
    if row.isnull().all():
        week_change_counter += 1

    week = math.ceil(week_change_counter / 2)
    return week, week_change_counter


def is_fight_row(row):
    """Check whether a row contains a fight result (indicated by '- W')."""
    return row.astype(str).str.contains("- W").any()


# ---------------------------------------------------------------------------
# Main parsing loop
# ---------------------------------------------------------------------------

def parse_fights(df):
    """Walk every row of the spreadsheet and build the fights table.

    Returns:
        pd.DataFrame: One row per fight with all metadata columns.
    """
    fight_ids = []
    brand_ids = []
    location_ids = []
    championship_ids = []
    fight_type_ids = []
    ppv_ids = []
    contenders = []
    months = []
    weeks = []

    current_brand = None
    current_location = None
    current_ppv = None
    current_championship = None
    current_month = None
    fight_counter = FIGHT_ID_START - 1
    week_change_counter = 0

    for index, row in df.iterrows():
        next_row = df.iloc[index + 1] if index + 1 < len(df) else None

        # --- Brand / PPV header ---
        brand, ppv, location = parse_brand_or_ppv(row)
        if brand is not None or ppv is not None:
            current_brand = brand
            current_ppv = ppv
            current_location = location

        # --- Championship header ---
        current_championship = parse_championship(row)

        # --- Contender indicator ---
        contender = parse_contender(row)

        # --- Fight type ---
        current_fight_type = determine_fight_type(row, next_row, current_ppv)

        # --- Month ---
        current_month = parse_month(row, current_month)

        # --- Week ---
        current_week, week_change_counter = update_week(row, week_change_counter)

        # --- Record fight if this row contains a result ---
        if is_fight_row(row):
            fight_counter += 1
            fight_ids.append(fight_counter)
            brand_ids.append(current_brand)
            location_ids.append(current_location)
            fight_type_ids.append(current_fight_type)
            championship_ids.append(current_championship)
            ppv_ids.append(current_ppv)
            contenders.append(contender)
            months.append(current_month)
            weeks.append(current_week)

    return pd.DataFrame({
        "Fight_ID": fight_ids,
        "Location_ID": location_ids,
        "Brand_ID": brand_ids,
        "PPV_ID": ppv_ids,
        "Championship_ID": championship_ids,
        "FightType_ID": fight_type_ids,
        "Season_ID": SEASON,
        "Month": months,
        "Week": weeks,
        "Contender_Indicator": contenders,
    })


def main():
    """Entry point: load data, parse fights, and write output CSV."""
    load_reference_data()  # validates that reference CSVs exist
    df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1")
    fight_df = parse_fights(df)

    # Convert numeric columns to integers (using nullable Int64 to handle NaN)
    int_columns = ["Fight_ID", "Brand_ID", "FightType_ID", "Season_ID"]
    for col in int_columns:
        if col in fight_df.columns:
            fight_df[col] = fight_df[col].astype("Int64")

    fight_df.to_csv(OUTPUT_CSV, index=False)


if __name__ == "__main__":
    main()
