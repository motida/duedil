import pandas as pd

COMPANIES_FILE = 'companies_UTF8.csv'

#with open("companies.csv") as file: # Use file to refer to the file object
#    df = pd.read_csv(file, encoding='utf-16')

df = pd.read_csv(COMPANIES_FILE)
companies = df.to_dict('records')
print(len(companies))
