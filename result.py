import pandas as pd
import math
import re

# Load the spreadsheet
file_path = r'/Users/ianjpeck/Documents/GitHub/sbparser/FullSeason5.xlsx'
spreadsheet = pd.ExcelFile(file_path)
result_id_start = 1

# Load the data from the first sheet
df = pd.read_excel(file_path, sheet_name='Sheet1')

# Extract relevant rows and reset the index for easier handling
fight_rows = df

results = []
fight_counter = 0
for index, row in fight_rows.iterrows():
    if row.astype(str).str.contains('- W').any():
        fight_counter += 1
    # Find Fighters
    if str(row[1]).isdigit():
        fighters = row.iloc[2:][row.iloc[2:].apply(lambda x: isinstance(x, str))].tolist()
        
        for fighter in fighters:
            if fighter not in ('Brawl', 'Melee', 'Ultimate'): # Remove Tournament Issues
                fighter_name = fighter.replace('- W','').replace('(PL)','').strip()
                decision = 'w' if '- W' in fighter else 'l'
                fighter_index = row[row == fighter].index[0]
                fighter_col_index = df.columns.get_loc(fighter_index)
                if index + 1 < len(df):
                    value_below = df.iloc[index + 1, fighter_col_index]
                    results.append({'Result_ID': result_id_start,'Fight_ID': fight_counter, 'Fighter': fighter_name, 'Match_Result': value_below, 'Decision': decision, 'Seed': None, 'DefendingIndicator': None})
                    result_id_start += 1

# Convert results to a DataFrame
results_df = pd.DataFrame(results)
results_df.to_csv('/Users/ianjpeck/Documents/GitHub/sbparser/result_test.csv', index=False)