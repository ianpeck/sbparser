import pandas as pd
import math
import re

# Load the spreadsheet
file_path = r'C:\Users\19202\Downloads\Season5.xlsx'
spreadsheet = pd.ExcelFile(file_path)

# Load the data from the first sheet
df = pd.read_excel(file_path, sheet_name='Sheet1')

# Extract relevant rows and reset the index for easier handling
fight_rows = df

fight_counter = 0
for index, row in fight_rows.iterrows():
    if row.astype(str).str.contains('- W').any():
        fight_counter += 1
    # Find Fighters
    if str(row[1]).isdigit():
        fighters = row.iloc[1:][row.apply(lambda x: isinstance(x, str))].tolist()
        print(fighters)