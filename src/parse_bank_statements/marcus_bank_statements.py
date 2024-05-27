import pdftotext
import os
import re
import pandas as pd
import gspread

BANK_STATEMENTS_FILE_PATH='/Users/jaredyu/Desktop/finances/finance_tracker_app/data/bank_statements'
CREDIT_CARD_STATEMENTS_FILE_PATH='/Users/jaredyu/Desktop/finances/finance_tracker_app/data/credit_card_statements'
SPREADSHEET_KEY=os.environ['SPREADSHEET_KEY']

def remove_indices(lst, indices):
    # Sort indices in descending order to avoid reindexing issues
    indices = sorted(indices, reverse=True)
    
    # Remove elements at each index
    for index in indices:
        if 0 <= index < len(lst):
            lst.pop(index)
        else:
            raise IndexError(f"Index {index} is out of bounds for list of length {len(lst)}")
    
    return lst

def parse_lines_with_regex(lines, transaction_pattern):
    # Ref.: https://levelup.gitconnected.com/creating-a-bank-statement-parser-with-python-9223b895ebae
    transactions = []
    for line in lines:
        match = re.search(pattern=transaction_pattern, string=line)
        if match:
            transactions.append(match.groupdict())

    return pd.DataFrame(transactions)

transaction_pattern = (
    r"(?P<transaction_date>\d+/\d+/\d+)\s*"
    r"(?P<description>.*?)(?=\$)"
    r"(?P<credit_debit>.*?)(?=\s)\s*"
    r"(?P<balance>.*)"
)

def currency_to_float(x):
    return float(x.replace('$', '').replace(',', ''))

def parse_marcus_bank_statements_by_year(bank, year, bank_statements_file_path):
    """
    Go through a year of monthly bank statements for a given bank and parse
    the statements and return a df.
    """
    file_path = os.path.join(bank_statements_file_path, bank, year)
    monthly_bank_statement_list = os.listdir(file_path)
    monthly_bank_statement_list = [i for i in monthly_bank_statement_list if i != '.DS_Store']
    transactions_df_list = []
    for monthly_bank_statement_file in monthly_bank_statement_list:
        month = monthly_bank_statement_file.split('_')[1].split('.')[0]
        with open(os.path.join(file_path, monthly_bank_statement_file), "rb") as file:
            pdf = pdftotext.PDF(file, physical=True)
            if len(pdf) == 1:
                first_page = pdf[0]
                lines1 = first_page.split("\n")
                lines1 = [i.lstrip() for i in lines1]
                lines1 = [i for i in lines1 if i != '']
                lines2 = None
            elif len(pdf) == 2:
                first_page = pdf[0]
                lines1 = first_page.split("\n")
                second_page = pdf[1]
                lines2 = second_page.split("\n")

                lines1 = [i.lstrip() for i in lines1]
                lines1 = [i for i in lines1 if i != '']
                lines2 = [i.lstrip() for i in lines2]
                lines2 = [i for i in lines2 if i != '']
            else:
                pdf_length = len(pdf)
                raise Exception(f'New length for pdf ({pdf_length}), time to set new rules. Info: {bank}, {year}, {month}')

        if lines2 is None:
            transactions_forward_list = lines1[lines1.index('ACCOUNT ACTIVITY'):]
        else:
            transactions_forward_list = lines1[lines1.index('ACCOUNT ACTIVITY'):] + lines2[lines2.index('ACCOUNT ACTIVITY (continued)'):]

        transaction_lines_list = transactions_forward_list
        transaction_lines_list = transaction_lines_list.copy()
        beginning_balance_list = transaction_lines_list.copy()

        # get the beginning entry for reference
        beginning_balance_entry = [i for i in beginning_balance_list if 'Beginning Balance' in i][0]
        beginning_balance_dict = re.search(
            pattern=(
                r"(?P<transaction_date>\d+/\d+/\d+)\s*"
                r"(?P<description>.*?)(?=\$)"
                r"(?P<balance>.*)"
            ),
            string=beginning_balance_entry
        ).groupdict()

        # parse the other lines
        date_pattern = r"^\d{2}/\d{2}/\d{4}"
        bad_idx_list = []
        for idx, txc_line in enumerate(transaction_lines_list):
            if not bool(re.match(date_pattern, txc_line[:10])):
                bad_idx_list.append(idx)

        transaction_lines_list = remove_indices(transaction_lines_list, bad_idx_list)
        transaction_lines_list = [
            i for i in transaction_lines_list if all(substring not in i for substring in ['Beginning Balance', 'Ending Balance'])
        ]

        transactions_df = parse_lines_with_regex(transaction_lines_list, transaction_pattern)
        transactions_df['credit_debit'] = transactions_df['credit_debit'].apply(currency_to_float)
        transactions_df['balance'] = transactions_df['balance'].apply(currency_to_float)
        beginning_balance_df = pd.DataFrame([beginning_balance_dict])
        beginning_balance_df['balance'] = beginning_balance_df['balance'].apply(currency_to_float)
        transactions_df = pd.concat(
            [
                beginning_balance_df,
                transactions_df
            ]
        )
        transactions_df['description'] = transactions_df['description'].apply(lambda x: x.rstrip())

        # for reversal charges which have negative values in the credit statement
        transactions_df['credit_debit'] = abs(transactions_df['credit_debit'])

        credit_debit_multiplier_list = []
        transactions_df.reset_index(drop=True, inplace=True) # fix idx for the iterrows
        for idx, row in transactions_df.iterrows():
            cur_balance = row['balance']
            if idx > 0:
                if cur_balance > prev_balance:
                    credit_debit_multiplier = 1
                else:
                    credit_debit_multiplier = -1
            else:
                credit_debit_multiplier = 1
            credit_debit_multiplier_list.append(credit_debit_multiplier)
            prev_balance = row['balance']

        transactions_df['credit_debit_multiplier'] = credit_debit_multiplier_list
        transactions_df['credit_debit'] = transactions_df['credit_debit'] * transactions_df['credit_debit_multiplier']
        transactions_df.drop(['credit_debit_multiplier'], axis=1, inplace=True)
        transactions_df = transactions_df.iloc[1:,:].copy() # drop the Beginning Balance
        transactions_df.sort_values(by='transaction_date', ascending=True, inplace=True)
        transactions_df_list.append(transactions_df)

    return pd.concat(transactions_df_list)

marcus_annual_beginning_ending_balance_df = pd.DataFrame({
    '2021': [0, 11719.53],
    '2022': [11719.53, 4877.32],
    '2023': [4877.32, 28770.03],
    '2024': [28770.03, 30478.36],
})

def approx_sum(x):
    return round(sum(x), 2)

def test_annual_balance_marcus(df, year, ref_df):
    tmp = round(ref_df[year][0] + approx_sum(df['credit_debit']), 2)
    assert tmp == ref_df[year][1]

transactions_2021_df = parse_marcus_bank_statements_by_year(
    bank='marcus',
    year='2021',
    bank_statements_file_path=BANK_STATEMENTS_FILE_PATH,
)
transactions_2022_df = parse_marcus_bank_statements_by_year(
    bank='marcus',
    year='2022',
    bank_statements_file_path=BANK_STATEMENTS_FILE_PATH,
)
transactions_2023_df = parse_marcus_bank_statements_by_year(
    bank='marcus',
    year='2023',
    bank_statements_file_path=BANK_STATEMENTS_FILE_PATH,
)
transactions_2024_df = parse_marcus_bank_statements_by_year(
    bank='marcus',
    year='2024',
    bank_statements_file_path=BANK_STATEMENTS_FILE_PATH,
)

# test for regressions
test_annual_balance_marcus(
    df=transactions_2021_df,
    year='2021',
    ref_df=marcus_annual_beginning_ending_balance_df
)
test_annual_balance_marcus(
    df=transactions_2022_df,
    year='2022',
    ref_df=marcus_annual_beginning_ending_balance_df
)
test_annual_balance_marcus(
    df=transactions_2023_df,
    year='2023',
    ref_df=marcus_annual_beginning_ending_balance_df
)
test_annual_balance_marcus(
    df=transactions_2024_df,
    year='2024',
    ref_df=marcus_annual_beginning_ending_balance_df
)

transactions_df = pd.concat([
    transactions_2021_df,
    transactions_2022_df,
    transactions_2023_df,
    transactions_2024_df,
])

transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date'])
transactions_df.sort_values(by='transaction_date', ascending=True, inplace=True)
transactions_df.reset_index(drop=True, inplace=True)
transactions_df['transaction_date'] = transactions_df['transaction_date'].astype(str)

gc = gspread.service_account()
finance_tracker_db_spreadsheet = gc.open_by_key(SPREADSHEET_KEY)
marcus_worksheet = finance_tracker_db_spreadsheet.worksheet('marcus_bank_statements')
marcus_worksheet.update([transactions_df.columns.values.tolist()] + transactions_df.values.tolist())
marcus_worksheet.format("C:D", {"numberFormat": {"type": "CURRENCY"}})

print("SUCCESS")