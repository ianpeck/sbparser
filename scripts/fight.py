"""Parse fight metadata from a Smash Bros tournament Excel spreadsheet.

Reads the Excel file specified in config.yaml and extracts one row per fight
with brand, location, PPV, championship, fight type, season, month, week, and
contender indicator. Outputs fight_test.csv.
"""

import math
import re
from difflib import SequenceMatcher
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
BRANDS_PER_WEEK = _config.get("brands_per_week", 2)

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
    championship_dict = dict(
        zip(df_championships["Championship_Name"].str.lower(), df_championships["Championship_ID"])
    )

    return location_dict, ppv_dict, championship_dict


def parse_brand_or_ppv(row):
    """Detect whether a row is a brand or PPV header.

    Brand/PPV headers have a value in column 1 but not in column 0, and the
    value is not a bare number (which would be a seed).

    Returns:
        tuple: (brand_id_or_None, ppv_name_or_None, location_string)
    """
    if pd.notna(row.iloc[1]) and pd.isna(row.iloc[0]) and not str(row.iloc[1]).isdigit():
        label = str(row.iloc[1]).strip()
        brand = BRANDS.get(label)
        ppv = label if label not in BRANDS else None
        location = str(row.iloc[2]).strip()
        return brand, ppv, location
    return None, None, None


_CONTENDER_THRESHOLD = 0.75
_CHAMPIONSHIP_THRESHOLD = 0.80


def _is_contender_word(word):
    """Return True if word is close enough to 'contender' (typo-tolerant)."""
    return SequenceMatcher(None, word, "contender").ratio() >= _CONTENDER_THRESHOLD


def _is_championship_word(word):
    """Return True if word is close enough to 'championship' (typo-tolerant)."""
    return SequenceMatcher(None, word, "championship").ratio() >= _CHAMPIONSHIP_THRESHOLD


def parse_championship(row):
    """Detect a championship match header row.

    Matches rows like "Brawl Championship" but excludes rows containing
    "spot" or "added" (those are contender matches, not title matches).
    For tournament-style championship rows with "vs.", extract just the
    championship name portion. The word "championship" is matched fuzzily
    to catch typos like "Champiosnhip".

    Returns:
        str or None: Championship name (normalized spelling) if detected, else None.
    """
    if pd.isna(row.iloc[0]):
        return None
    words = str(row.iloc[0]).strip().split()
    if not words or not _is_championship_word(words[-1].lower()):
        return None
    text_lower = str(row.iloc[0]).lower().strip()
    if re.search(r"\b(spot|added)\b", text_lower):
        return None
    # Normalize the last word to "Championship" regardless of original spelling
    if "vs." in text_lower:
        # e.g. "1 vs. 4 - Brawl Champiosnhip" → "Brawl Championship"
        remainder = " ".join(words[3:-1] + ["Championship"])
        return remainder.lstrip("- ").strip()
    return " ".join(words[:-1] + ["Championship"])


def parse_contender(row):
    """Detect a #1 contender or "spot in <championship>" match.

    The "contender" word is matched fuzzily to catch typos like "conteder".

    Returns:
        str or None: The contender description if detected, else None.
    """
    if pd.notna(row.iloc[0]):
        text_lower = str(row.iloc[0]).lower().strip()
        # "#1 <contender-ish> <name>" pattern — fuzzy match on the middle word
        m = re.match(r"^#1\s+(\w+)\s+(\w+)$", text_lower)
        if m and _is_contender_word(m.group(1)):
            return "Y"
        champ_pattern = "|".join(re.escape(c.lower()) for c in CHAMPIONSHIP_NAMES)
        # "Spot in <championship>" pattern
        if re.findall(rf"^spot in ({champ_pattern})$", text_lower):
            return "Y"
        # "Beat the clock for <championship> spot" pattern
        if re.findall(rf"^beat the clock for ({champ_pattern}) spot$", text_lower):
            return "Y"
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
    if pd.isna(row.iloc[0]):
        return FIGHT_TYPES["Three Stock"]

    text = str(row.iloc[0])
    text_lower = text.lower().strip()
    next_text_lower = str(next_row.iloc[0]).lower().strip() if next_row is not None else ""

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
    ] and pd.notna(next_row.iloc[0]) if next_row is not None else False:
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
    if pd.notna(row.iloc[0]) and "Month" in str(row.iloc[0]):
        return str(row.iloc[0]).replace("Month ", "")
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
    if pd.notna(row.iloc[0]) and "Month" in str(row.iloc[0]):
        week_change_counter = 0

    # A fully-blank row signals a show boundary
    if row.isnull().all():
        week_change_counter += 1

    week = math.ceil(week_change_counter / BRANDS_PER_WEEK)
    return week, week_change_counter


def is_fight_row(row):
    """Check whether a row contains a fight result (indicated by '- W')."""
    return row.astype(str).str.contains("- W").any()


# ---------------------------------------------------------------------------
# Main parsing loop
# ---------------------------------------------------------------------------

def parse_fights(df, location_dict, ppv_dict, championship_dict):
    """Walk every row of the spreadsheet and build the fights table.

    Args:
        df: The raw spreadsheet DataFrame.
        location_dict: Mapping of lowercase location name → Location_ID.
        ppv_dict: Mapping of lowercase PPV name → PPV_ID.
        championship_dict: Mapping of lowercase championship name → Championship_ID.

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
    current_location_id = None
    current_ppv = None        # PPV name — kept as string for fight-type logic
    current_ppv_id = None     # PPV ID — written to output
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
            current_ppv_id = ppv_dict.get(ppv.lower()) if ppv else None
            current_location_id = location_dict.get(location.lower()) if location else None

        # --- Championship header (row-level: championship header and fight are on the same row) ---
        champ_name = parse_championship(row)
        if champ_name is not None:
            champ_key = re.sub(r"\s+championship$", "", champ_name.lower().strip())
            championship_id = championship_dict.get(champ_key)
        else:
            championship_id = None

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
            location_ids.append(current_location_id)
            fight_type_ids.append(current_fight_type)
            championship_ids.append(championship_id)
            ppv_ids.append(current_ppv_id)
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
    location_dict, ppv_dict, championship_dict = load_reference_data()
    df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1")
    fight_df = parse_fights(df, location_dict, ppv_dict, championship_dict)

    # Convert numeric columns to integers (using nullable Int64 to handle NaN)
    int_columns = ["Fight_ID", "Location_ID", "Brand_ID", "PPV_ID", "Championship_ID", "FightType_ID", "Season_ID"]
    for col in int_columns:
        if col in fight_df.columns:
            fight_df[col] = fight_df[col].astype("Int64")

    fight_df.to_csv(OUTPUT_CSV, index=False)


if __name__ == "__main__":
    main()
