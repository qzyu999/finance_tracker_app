import pdftotext
import os
import re
import pandas as pd
import gspread

BANK_STATEMENTS_FILE_PATH='/Users/jaredyu/Desktop/finances/finance_tracker_app/data/bank_statements'
SPREADSHEET_KEY=os.environ['SPREADSHEET_KEY']
WORKSHEET_NAME='east_west_bank_bank_statements'

def pair_sequentially(numbers):
    # Check if the list has an even length
    if len(numbers) % 2 != 0:
        raise ValueError("The list must have an even length")

    # Create the list of pairs
    paired_list = []
    for i in range(0, len(numbers), 2):
        paired_list.append(numbers[i:i+2])
    
    return paired_list

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

def has_consecutive_values(data):
  """
  This function checks if a list contains any consecutive values (adjacent duplicates).

  Args:
      data: A list of any data type.

  Returns:
      True if there are consecutive values, False otherwise.
  """
  if len(data) <= 1:
    return False  # Need at least 2 elements for consecutive values

  # Iterate through the list, checking for adjacent duplicates
  for i in range(1, len(data)):
    if data[i] == data[i-1] + 1:
      return True
  return False

def concatenate_multi_line_transactions(transaction_lines_list, bank, year, month):
    """
    Edit credit and debit line lists to concatenate strings from multi-line items.
    """
    transaction_lines_list = transaction_lines_list.copy()
    date_pattern = r"^\d{2}-\d{2}$"
    bad_idx_list = []
    for idx, txc_line in enumerate(transaction_lines_list):
        if not bool(re.match(date_pattern, txc_line[:5])):
            bad_idx_list.append(idx)

    if has_consecutive_values(data=bad_idx_list):
        raise Exception(f'Transactions with more than two lines found. Info: {bank}, {year}, {month}')

    if len(bad_idx_list) > 0:
        complete_bad_idx_list = []
        for i in bad_idx_list:
            complete_bad_idx_list.append(i - 1)
            complete_bad_idx_list.append(i)

        paired_short_line_list = pair_sequentially(complete_bad_idx_list)

        # extract them from the original list and concatenate them together
        combined_line_list = []
        for paired_lines in paired_short_line_list:
            combined_line = ''.join(transaction_lines_list[paired_lines[0]:paired_lines[1]+1])
            combined_line_list.append(combined_line)

        # drop the original items
        transaction_lines_list = remove_indices(transaction_lines_list, complete_bad_idx_list)

        return transaction_lines_list + combined_line_list
    else:
        return transaction_lines_list

def parse_lines_with_regex(lines, transaction_pattern):
    # Ref.: https://levelup.gitconnected.com/creating-a-bank-statement-parser-with-python-9223b895ebae
    transactions = []
    for line in lines:
        match = re.search(pattern=transaction_pattern, string=line)
        if match:
            transactions.append(match.groupdict())

    return pd.DataFrame(transactions)

transaction_pattern = (
        r"(?P<transaction_date>\d+-\d+)\s*"
        r"(?P<description>.*?)\s*"
        r"(?P<amount>[\d.,]+)$"
)

def parse_east_west_bank_bank_statements_by_year(bank, year, bank_statements_file_path):
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
            if len(pdf) == 2:
                first_page = pdf[0]
                lines1 = first_page.split("\n")
                lines1 = [i.lstrip() for i in lines1]
                lines1 = [i for i in lines1 if i != '']
                lines2 = None
            elif len(pdf) == 3:
                first_page = pdf[0]
                second_page = pdf[1]
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
            
            # for line in lines1:
            #     print(line.lstrip())

        try:
            credits_line_idx = lines1.index('CREDITS')
            credit_balance_exists = True
        except:
            credit_balance_exists = False
        try:
            debits_line_idx = lines1.index('DEBITS')
            debits_line_on_first_page = True
        except:
            debits_line_on_first_page = False
            raise Exception(f'DEBITS not on first page, time to set new rules. Info: {bank}, {year}, {month}')

        try:
            daily_balances_line_idx = lines1.index('DAILY BALANCES')
            daily_balances_on_first_page = True
        except:
            daily_balances_line_idx = lines2.index('DAILY BALANCES')
            daily_balances_on_first_page = False
        credit_lines = lines1[credits_line_idx + 2:debits_line_idx]

        try: # check if the DEBITS balance is multi-page
            if len([i for i in lines2 if i[:4] == 'Date']) > 1:
                debit_balance_multi_page = True
            else:
                debit_balance_multi_page = False
        except:
            debit_balance_multi_page = False

        # No CREDITS and DEBITS does not extend to second
        if not credit_balance_exists and not debit_balance_multi_page:
            debit_lines = lines1[debits_line_idx + 2:daily_balances_line_idx]
            debit_lines = concatenate_multi_line_transactions(debit_lines, bank, year, month)
            debit_df = parse_lines_with_regex(lines=debit_lines, transaction_pattern=transaction_pattern)
            debit_df['amount'] = debit_df['amount'].apply(lambda x: -1 * float(x.replace(',' , '')))

            # debit_df['bank'] = bank
            debit_df['year'] = year
            debit_df['month'] = month
            transactions_df_list.append(debit_df)
            continue
        # DAILY BALANCES on first page and DEBITS does not extend to second
        elif daily_balances_on_first_page and not debit_balance_multi_page:
            debit_lines = lines1[debits_line_idx + 2:daily_balances_line_idx]
        # DEBITS on first page but extends to second
        elif debits_line_on_first_page and debit_balance_multi_page:
            second_page_debit_date_line_idx = lines2.index([i for i in lines2 if i[:4] == 'Date'][0])
            debit_lines = lines1[debits_line_idx + 2:] + lines2[second_page_debit_date_line_idx + 1:daily_balances_line_idx]
        # DAILY BALANCES not on first page and DEBITS does not extend to second
        elif not daily_balances_on_first_page and not debit_balance_multi_page:
            debit_lines = lines1[debits_line_idx + 2:]
        else:
            raise Exception(f'Uncaught case. Info: {bank}, {year}, {month}')

        credit_lines = concatenate_multi_line_transactions(credit_lines, bank, year, month)
        debit_lines = concatenate_multi_line_transactions(debit_lines, bank, year, month)

        credit_df = parse_lines_with_regex(lines=credit_lines, transaction_pattern=transaction_pattern)
        debit_df = parse_lines_with_regex(lines=debit_lines, transaction_pattern=transaction_pattern)

        credit_df['amount'] = credit_df['amount'].apply(lambda x: float(x.replace(',' , '')))
        debit_df['amount'] = debit_df['amount'].apply(lambda x: -1 * float(x.replace(',' , '')))

        transactions_df = pd.concat([credit_df, debit_df])

        # transactions_df['bank'] = bank
        transactions_df['year'] = year
        transactions_df['month'] = month
        transactions_df_list.append(transactions_df)

    combined_transactions_df = pd.concat(transactions_df_list)

    return combined_transactions_df

east_west_bank_annual_beginning_ending_balance_df = pd.DataFrame({
    '2020': [2459.25, 15619.65],
    '2021': [15619.65, 14552.04],
    '2022': [14552.04, 3046.51],
    '2023': [3046.51, 19634.88],
    '2024': [19634.88, 2982.74],
})

# transactions_2019_df = parse_bank_statements_by_year(
#     bank='east_west_bank',
#     year='2019',
#     bank_statements_file_path=BANK_STATEMENTS_FILE_PATH,
# )

transactions_2020_df = parse_east_west_bank_bank_statements_by_year(
    bank='east_west_bank',
    year='2020',
    bank_statements_file_path=BANK_STATEMENTS_FILE_PATH,
)
transactions_2021_df = parse_east_west_bank_bank_statements_by_year(
    bank='east_west_bank',
    year='2021',
    bank_statements_file_path=BANK_STATEMENTS_FILE_PATH,
)
transactions_2022_df = parse_east_west_bank_bank_statements_by_year(
    bank='east_west_bank',
    year='2022',
    bank_statements_file_path=BANK_STATEMENTS_FILE_PATH,
)
transactions_2023_df = parse_east_west_bank_bank_statements_by_year(
    bank='east_west_bank',
    year='2023',
    bank_statements_file_path=BANK_STATEMENTS_FILE_PATH,
)
transactions_2024_df = parse_east_west_bank_bank_statements_by_year(
    bank='east_west_bank',
    year='2024',
    bank_statements_file_path=BANK_STATEMENTS_FILE_PATH,
)

def approx_sum(x):
    return round(sum(x), 2)

def test_annual_balance_east_west_bank(df, year, ref_df):
    tmp = round(ref_df[year][0] + approx_sum(df['amount']), 2)
    assert tmp == ref_df[year][1]

# test for regressions
test_annual_balance_east_west_bank(
    df=transactions_2020_df,
    year='2020',
    ref_df=east_west_bank_annual_beginning_ending_balance_df
)
test_annual_balance_east_west_bank(
    df=transactions_2021_df,
    year='2021',
    ref_df=east_west_bank_annual_beginning_ending_balance_df
)
test_annual_balance_east_west_bank(
    df=transactions_2022_df,
    year='2022',
    ref_df=east_west_bank_annual_beginning_ending_balance_df
)
test_annual_balance_east_west_bank(
    df=transactions_2023_df,
    year='2023',
    ref_df=east_west_bank_annual_beginning_ending_balance_df
)
test_annual_balance_east_west_bank(
    df=transactions_2024_df,
    year='2024',
    ref_df=east_west_bank_annual_beginning_ending_balance_df
)

total_transactions_df = pd.concat([
    transactions_2020_df,
    transactions_2021_df,
    transactions_2022_df,
    transactions_2023_df,
    transactions_2024_df
])

total_transactions_df['transaction_date_month'] = total_transactions_df['transaction_date'].apply(lambda x: x.split('-')[0])
assert sum(total_transactions_df['transaction_date_month'] != total_transactions_df['month']) == 0
total_transactions_df['transaction_date'] = total_transactions_df['year'] + '-' + total_transactions_df['transaction_date']
total_transactions_df.drop(['year', 'month', 'transaction_date_month'], inplace=True, axis=1)
total_transactions_df.sort_values(by=['transaction_date', 'amount', 'description'], ascending=[True, False, True], inplace=True)
total_transactions_df.reset_index(drop=True, inplace=True)

gc = gspread.service_account()

finance_tracker_db_spreadsheet = gc.open_by_key(SPREADSHEET_KEY)
east_west_bank_worksheet = finance_tracker_db_spreadsheet.worksheet(WORKSHEET_NAME)
east_west_bank_worksheet.update([total_transactions_df.columns.values.tolist()] + total_transactions_df.values.tolist())

print("SUCCESS")