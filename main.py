from calendar import week
from cmath import isnan
import pandas as pd
import math
import re

# Load the spreadsheet
file_path = r'C:\Users\19202\GitHub\sbparser\FullSeason5.xlsx'
spreadsheet = pd.ExcelFile(file_path)
season = 5

# Load the data from the first sheet
df = pd.read_excel(file_path, sheet_name='Sheet1')

# Extract relevant rows and reset the index for easier handling
fight_rows = df

# Initialize lists to store data
fight_ids = []
brand_ids = []
location_ids = []
championship_ids = []
fight_type_ids = []
ppv_ids = []
contenders = []
months = []
weeks = []

# Variables to keep track of the current brand, location, and championship
current_brand = None
current_location = None
current_championship = None

# Loop through the DataFrame to assign Fight_ID, Brand_ID, Location_ID, PPV_ID, and Championship_ID
fight_counter = 0
week_change_counter = 0
for index, row in fight_rows.iterrows():
    # -----------------------------------------
    # Check for brand or PPV names
    # -----------------------------------------
    if pd.notna(row[1]) and pd.isna(row[0]) and not str(row[1]).isdigit():
        current_brand = str(row[1]).strip() if str(row[1]).strip() in ['Ultimate', 'Melee', 'Brawl'] else None
        current_ppv = str(row[1]).strip() if str(row[1]).strip() not in ['Ultimate', 'Melee', 'Brawl'] else None
        current_location = row[2]  # Get the location from the right-adjacent cell
    # -----------------------------------------
    # Check for Championship or # 1 contender matches
    # -----------------------------------------
    if pd.notna(row[0]) and re.findall(r'^(?!.*\bspot\b).* championship$', str(row[0]).lower()):
        current_championship = row[0]
    else:
        current_championship = None
    if pd.notna(row[0]) and re.findall(r'^#1 contender \w+$', str(row[0]).lower()):
        contender = row[0]
    else:
        contender = None
    # -----------------------------------------
    # Check for fight type
    # -----------------------------------------
    if pd.notna(row[0]) and 'Tag' in str(row[0]):
        current_fight_type = 12 # Tag
    elif pd.notna(row[0]) and 'Coin' in str(row[0]):
        current_fight_type = 3 # Coin
    elif pd.notna(row[0]) and 'Hardcore' in str(row[0]):
        current_fight_type = 2 # 3 Minute
    elif pd.notna(row[0]) and str(row[0]).strip() == 'Royal Rumble':
        current_fight_type = 8
    elif pd.notna(row[0]) and str(row[0]).strip() == 'Pokeball Match':
        current_fight_type = 7
    else:
        current_fight_type = 1 # 3 stock
    # -----------------------------------------
    # Check for current month
    # -----------------------------------------
    if pd.notna(row[0]) and 'Month' in str(row[0]):
        current_month = str(row[0]).replace('Month ', '')
    # -----------------------------------------
    # Check for current week
    # -----------------------------------------
    # make sure it resets after the month is complete
    if pd.notna(row[0]) and 'Month' in str(row[0]):
        week_change_counter = 0 
    # add 1 if ran all NULL row appears, signfiying a jump to the next show
    if row.isnull().all():
        week_change_counter += 1
    # round up
    current_week = math.ceil(week_change_counter / 2)

    # -----------------------------------------
    # Check if a fight is listed
    # -----------------------------------------
    if row.astype(str).str.contains('- W').any():
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

# Create the DataFrame with everything in both Brand_ID and PPV_ID
fight_id_df = pd.DataFrame({
    'Fight_ID': fight_ids,
    'Brand_ID': brand_ids,
    'Location_ID': location_ids,
    'PPV_ID': ppv_ids,
    'Championship_ID': championship_ids,
    'FightType_ID': fight_type_ids,
    'Season_ID': season,
    'Month': months,
    'Week': weeks,
    '#1ContenderIndicator': contenders
})

fight_id_df.to_csv(r'C:\Users\19202\GitHub\sbparser\test.csv')