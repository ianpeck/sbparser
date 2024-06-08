import pandas as pd
import math
import re

# Load the spreadsheet
file_path = r'/Users/ianjpeck/Documents/GitHub/sbparser/FullSeason5.xlsx'
spreadsheet = pd.ExcelFile(file_path)
result_id_start = 4324 # Season 5

# Load the data from the first sheet
df = pd.read_excel(file_path, sheet_name='Sheet1')

# Extract relevant rows and reset the index for easier handling
fight_rows = df

results = []
fight_counter = 1910 # Season 5
for index, row in fight_rows.iterrows():
    if row.astype(str).str.contains('- W').any():
        fight_counter += 1 # increment to next fight each time a - W is seen in a row (confirmed there are no issues with this)
    # Find Fighters
    if str(row[1]).isdigit():
        fighters = row.iloc[2:][row.iloc[2:].apply(lambda x: isinstance(x, str))].tolist() # fighters can only appear past column 2
        
        for fighter in fighters:
            if fighter not in ('Brawl', 'Melee', 'Ultimate'): # Remove Tournament Issues where it would catch these strings
                fighter_name = fighter.replace('- W','').replace('(PL)','').replace('(Defending)','').replace('.','').strip()
                decision = 'w' if '- W' in fighter else 'l'
                fighter_index = row[row == fighter].index[0]
                fighter_col_index = df.columns.get_loc(fighter_index)
                if row.astype(str).str.contains('vs.').any():
                    seed_string = df.iloc[index, 0]
                    if fighter_col_index == 2:
                        seed = seed_string.split()[0] # first cell is first seed
                    elif fighter_col_index == 3:
                        seed = seed_string.split()[2] # second cell is whatever comes after 'vs.'
                else:
                    seed = None
                if pd.notna(row[0]) and re.findall(r'^(?!.*\b(spot|added)\b).* championship$', str(row[0]).lower()):
                    # fighter is not defending if a tourney or scramble (vs.) match occurs without the string 'Defending' in name
                    if 'vs.' in str(row[0]).lower() and '(Defending)' not in fighter: 
                        defending = None
                    elif fighter_col_index == 2:
                        defending = 'Y'
                    elif fighter_col_index == 3 and str(row[0].lower()) == 'unified tag team championship':
                        defending = 'Y' # also gets teammate of tag champion in first cell
                    else:
                        defending = None
                elif '(Defending)' in fighter: # used to catch Scramble and Tourney Defenders (1 seeds for example)
                        defending = 'Y'
                else:
                    defending = None
                if index + 1 < len(df):
                    value_below = str(df.iloc[index + 1, fighter_col_index]).replace('HP','').strip() # grab result which is below fighter name cell
                    results.append({'Result_ID': result_id_start, 'Fighter_Name': fighter_name, 'Fight_ID': fight_counter, 'Decision': decision, 'Match_Result': value_below, 'Seed': seed, 'DefendingIndicator': defending})
                    result_id_start += 1

# Convert results to a DataFrame
results_df = pd.DataFrame(results)
results_df.to_csv('/Users/ianjpeck/Documents/GitHub/sbparser/result_test.csv', index=False)