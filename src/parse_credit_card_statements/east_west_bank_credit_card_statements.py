import pdftotext
import os
import re
import pandas as pd
import gspread

CREDIT_CARD_STATEMENTS_FILE_PATH='/Users/jaredyu/Desktop/finances/finance_tracker_app/data/credit_card_statements/'
SPREADSHEET_KEY=os.environ['SPREADSHEET_KEY']
WORKSHEET_NAME='east_west_bank_credit_card_statements'

east_west_bank_credit_card_annual_beginning_ending_balance_df = pd.DataFrame({
    '2017': [1937.56, 1748.56],
    '2018': [1748.56, 1790.84],
    '2019': [1790.84, 45.21],
    '2020': [45.21, 1080.03],
    '2021': [1080.03, 99.31],
    '2022': [99.31, 137.52],
    '2023': [137.52, 82.56],
    '2024': [82.56, -275.03],
})

def parse_lines_with_regex(lines, transaction_pattern):
    # Ref.: https://levelup.gitconnected.com/creating-a-bank-statement-parser-with-python-9223b895ebae
    transactions = []
    for line in lines:
        match = re.search(pattern=transaction_pattern, string=line)
        if match:
            transactions.append(match.groupdict())

    return pd.DataFrame(transactions)

transaction_pattern = (
    r"(?P<post_date>\d{2}/\d{2})\s*"
    r"(?P<transaction_date>\d{2}/\d{2})\s*"
    r"(?P<ref_num>\S*)\s*"
    r"(?P<description>.*?)(?=\$)"
    r"(?P<amount>\S.*)"
)

def clean_amount_col(x):
    # remove ($), (,), (alphabetical)
    return float(re.sub(r"[^\d|\.]", "", x.replace('$', '')))

def check_list_len_bool(l):
    if len(l) > 0:
        return True
    else:
        return False

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

def drop_multiline_transactions(transaction_lines):
    transaction_lines = transaction_lines.copy()
    bad_idx_list = []
    for idx, i in enumerate(transaction_lines):
        # if not bool(re.match(r"^(\d{2}/\d{2})\s*(\d{2}/\d{2})", i)):
        if not bool(re.match(r"^(\d{2}/\d{2})\s*", i)):
            bad_idx_list.append(idx)
    transaction_lines = remove_indices(lst=transaction_lines, indices=bad_idx_list)
    return transaction_lines

def insert_na_for_missing_txn_date_and_ref_num(transaction_lines):
    # works only for when there's a post date and no transaction date
    null_idx_list = []
    for idx, i in enumerate(transaction_lines):
        if bool(re.match(r"^(\d{2}/\d{2})\s{8,}", i)):
            null_idx_list.append(idx)

    for idx in null_idx_list:
        transaction_lines[idx] = transaction_lines[idx][:8] + \
            transaction_lines[idx][:5] + \
            '    NA' + \
            transaction_lines[idx][10:]
    return transaction_lines

def process_transaction_lines(
    payments_and_other_credits_lines=[],
    purchases_and_other_debits_lines=[],
    fees_lines=[],
    interest_charged_lines=[],
):
    """
    Return the transactions df from the transaction lines.
    """
    try:
        payments_and_other_credits_lines = drop_multiline_transactions(payments_and_other_credits_lines)
        payments_and_other_credits_lines = insert_na_for_missing_txn_date_and_ref_num(payments_and_other_credits_lines)
        payments_and_other_credits_df = parse_lines_with_regex(payments_and_other_credits_lines, transaction_pattern)
        payments_and_other_credits_df['amount'] = payments_and_other_credits_df['amount'].apply(clean_amount_col)
        payments_and_other_credits_df['amount'] = payments_and_other_credits_df['amount'] * -1 # make negative
    except:
        payments_and_other_credits_df = pd.DataFrame([])
    try:
        purchases_and_other_debits_lines = drop_multiline_transactions(purchases_and_other_debits_lines)
        purchases_and_other_debits_lines = insert_na_for_missing_txn_date_and_ref_num(purchases_and_other_debits_lines)
        purchases_and_other_debits_df = parse_lines_with_regex(purchases_and_other_debits_lines, transaction_pattern)
        purchases_and_other_debits_df['amount'] = purchases_and_other_debits_df['amount'].apply(clean_amount_col)
    except:
        purchases_and_other_debits_df = pd.DataFrame([])
    try:
        fees_lines = drop_multiline_transactions(fees_lines)
        fees_lines = insert_na_for_missing_txn_date_and_ref_num(fees_lines)
        fees_df = parse_lines_with_regex(fees_lines, transaction_pattern)
        fees_df['amount'] = fees_df['amount'].apply(clean_amount_col)
    except:
        fees_lines_df = pd.DataFrame([])
    try:
        interest_charged_lines = drop_multiline_transactions(interest_charged_lines)
        interest_charged_lines = insert_na_for_missing_txn_date_and_ref_num(interest_charged_lines)
        interest_charged_df = parse_lines_with_regex(interest_charged_lines, transaction_pattern)
        interest_charged_df['amount'] = interest_charged_df['amount'].apply(clean_amount_col)
    except:
        interest_charged_df = pd.DataFrame([])

    transactions_df = pd.concat([
        payments_and_other_credits_df,
        purchases_and_other_debits_df,
        fees_df,
        interest_charged_df,
    ])
    transactions_df.drop(['ref_num'], axis=1, inplace=True)
    return transactions_df

def add_year_to_date(first_page, transactions_df):
    """
    Add the year to the date columns. Handle cases with two years (Jan/Dec).
    """
    date_range = first_page.split("\n")[0].split('Statement')[1].split('Page')[0].lstrip().rstrip()
    start_date = date_range.split(' - ')[0]
    end_date = date_range.split(' - ')[1]
    start_year = start_date[6:]
    start_month = start_date[:2]
    end_year = end_date[6:]
    end_month = end_date[:2]
    if start_year == end_year:
        transactions_df['post_date'] = transactions_df['post_date'] + '/' + start_year
        transactions_df['transaction_date'] = transactions_df['transaction_date'] + '/' + start_year
    else:
        month_year_mapping = {
            start_month: start_year,
            end_month: end_year,
        }
        transactions_df['post_date_month'] = transactions_df['post_date'].apply(lambda x: x.split('/')[0])
        transactions_df['transaction_date_month'] = transactions_df['transaction_date'].apply(lambda x: x.split('/')[0])
        transactions_df['post_date'] = transactions_df['post_date'] + \
            '/' + \
            transactions_df['post_date_month'].apply(lambda x: month_year_mapping[x])
        transactions_df['transaction_date'] = transactions_df['transaction_date'] + \
            '/' + \
            transactions_df['transaction_date_month'].apply(lambda x: month_year_mapping[x])
        transactions_df.drop(['post_date_month', 'transaction_date_month'], axis=1, inplace=True)

    transactions_df['date_range'] = date_range
    return transactions_df

def check_for_indices(lines, keyword, exact_match=True):
    idx_list = []
    for idx, i in enumerate(lines):
        if exact_match:
            if i == keyword:
                idx_list.append(idx)
        else:
            if i[:len(keyword)] == keyword:
                idx_list.append(idx)
    return idx_list

def parse_east_west_bank_credit_card_statements_by_year(credit_card, year, credit_card_statements_file_path):
    """
    Go through a year of monthly bank statements for a given bank and parse
    the statements and return a df.
    """
    file_path = os.path.join(credit_card_statements_file_path, credit_card, year)
    monthly_credit_card_statement_list = os.listdir(file_path)
    monthly_credit_card_statement_list = [i for i in monthly_credit_card_statement_list if i != '.DS_Store']
    transactions_df_list = []
    for monthly_credit_card_statement_file in monthly_credit_card_statement_list:
        month = monthly_credit_card_statement_file.split('_')[1].split('.')[0]
        with open(os.path.join(file_path, monthly_credit_card_statement_file), "rb") as file:
            pdf = pdftotext.PDF(file, physical=True)

        # collect lines
        lines_list = []
        for page in pdf:
            lines = page.split("\n")
            lines = [i.lstrip() for i in lines]
            lines = [i for i in lines if i != '']
            if [i for i in lines if 'Transactions' in i]:
                lines_list += lines

        payments_and_other_credits_start_idx_list = check_for_indices(lines_list, 'Payments and Other Credits')
        purchases_and_other_debits_start_idx_list = check_for_indices(lines_list, 'Purchases and Other Debits')
        total_this_period_idx_list = check_for_indices(lines_list, 'TOTAL THIS PERIOD', False)
        fees_start_idx_list = check_for_indices(lines_list, 'Fees')
        total_fees_this_period_idx_list = check_for_indices(lines_list, 'TOTAL FEES THIS PERIOD', False)
        interest_charged_start_idx_list = check_for_indices(lines_list, 'Interest Charged')
        interest_charged_idx_list = check_for_indices(lines_list, 'TOTAL INTEREST THIS PERIOD', False)
        if payments_and_other_credits_start_idx_list:
            payments_and_other_credits_lines = lines_list[
                payments_and_other_credits_start_idx_list[0] + 3: \
                total_this_period_idx_list[0]
            ]
        else:
            payments_and_other_credits_lines = []
        if purchases_and_other_debits_start_idx_list:
            purchases_and_other_debits_lines = lines_list[
                purchases_and_other_debits_start_idx_list[0] + 3: \
                total_this_period_idx_list[-1]
            ]
        else:
            purchases_and_other_debits_lines = []
        if fees_start_idx_list:
            fees_lines = lines_list[
                fees_start_idx_list[0] + 3: \
                total_fees_this_period_idx_list[0]
            ]
        else:
            fees_lines = []
        if interest_charged_start_idx_list:
            interest_charged_lines = lines_list[
                interest_charged_start_idx_list[0] + 3: \
                interest_charged_idx_list[0]
            ]
        else:
            interest_charged_lines = []

        transactions_df = process_transaction_lines(
            payments_and_other_credits_lines,
            purchases_and_other_debits_lines,
            fees_lines,
            interest_charged_lines,
        )
        transactions_df = add_year_to_date(pdf[2], transactions_df)
        transactions_df_list.append(transactions_df)
    return pd.concat(transactions_df_list)

transactions_2017_df = parse_east_west_bank_credit_card_statements_by_year(
    credit_card='east_west_bank',
    year='2017',
    credit_card_statements_file_path=CREDIT_CARD_STATEMENTS_FILE_PATH,
)
transactions_2018_df = parse_east_west_bank_credit_card_statements_by_year(
    credit_card='east_west_bank',
    year='2018',
    credit_card_statements_file_path=CREDIT_CARD_STATEMENTS_FILE_PATH,
)
transactions_2019_df = parse_east_west_bank_credit_card_statements_by_year(
    credit_card='east_west_bank',
    year='2019',
    credit_card_statements_file_path=CREDIT_CARD_STATEMENTS_FILE_PATH,
)
transactions_2020_df = parse_east_west_bank_credit_card_statements_by_year(
    credit_card='east_west_bank',
    year='2020',
    credit_card_statements_file_path=CREDIT_CARD_STATEMENTS_FILE_PATH,
)
transactions_2021_df = parse_east_west_bank_credit_card_statements_by_year(
    credit_card='east_west_bank',
    year='2021',
    credit_card_statements_file_path=CREDIT_CARD_STATEMENTS_FILE_PATH,
)
transactions_2022_df = parse_east_west_bank_credit_card_statements_by_year(
    credit_card='east_west_bank',
    year='2022',
    credit_card_statements_file_path=CREDIT_CARD_STATEMENTS_FILE_PATH,
)
transactions_2023_df = parse_east_west_bank_credit_card_statements_by_year(
    credit_card='east_west_bank',
    year='2023',
    credit_card_statements_file_path=CREDIT_CARD_STATEMENTS_FILE_PATH,
)
transactions_2024_df = parse_east_west_bank_credit_card_statements_by_year(
    credit_card='east_west_bank',
    year='2024',
    credit_card_statements_file_path=CREDIT_CARD_STATEMENTS_FILE_PATH,
)

def approx_sum(x):
    return round(sum(x), 2)

def test_annual_balance_east_west_bank_credit_card(df, year, ref_df):
    tmp = round(ref_df[year][0] + approx_sum(df['amount']), 2)
    assert tmp == ref_df[year][1]

# test for regressions
test_annual_balance_east_west_bank_credit_card(
    df=transactions_2017_df,
    year='2017',
    ref_df=east_west_bank_credit_card_annual_beginning_ending_balance_df
)
test_annual_balance_east_west_bank_credit_card(
    df=transactions_2018_df,
    year='2018',
    ref_df=east_west_bank_credit_card_annual_beginning_ending_balance_df
)
test_annual_balance_east_west_bank_credit_card(
    df=transactions_2019_df,
    year='2019',
    ref_df=east_west_bank_credit_card_annual_beginning_ending_balance_df
)
test_annual_balance_east_west_bank_credit_card(
    df=transactions_2020_df,
    year='2020',
    ref_df=east_west_bank_credit_card_annual_beginning_ending_balance_df
)
test_annual_balance_east_west_bank_credit_card(
    df=transactions_2021_df,
    year='2021',
    ref_df=east_west_bank_credit_card_annual_beginning_ending_balance_df
)
test_annual_balance_east_west_bank_credit_card(
    df=transactions_2022_df,
    year='2022',
    ref_df=east_west_bank_credit_card_annual_beginning_ending_balance_df
)
test_annual_balance_east_west_bank_credit_card(
    df=transactions_2023_df,
    year='2023',
    ref_df=east_west_bank_credit_card_annual_beginning_ending_balance_df
)
test_annual_balance_east_west_bank_credit_card(
    df=transactions_2024_df,
    year='2024',
    ref_df=east_west_bank_credit_card_annual_beginning_ending_balance_df
)

total_transactions_df = pd.concat([
    transactions_2017_df,
    transactions_2018_df,
    transactions_2019_df,
    transactions_2020_df,
    transactions_2021_df,
    transactions_2022_df,
    transactions_2023_df,
    transactions_2024_df
])

total_transactions_df['post_date_fmt'] = pd.to_datetime(total_transactions_df['post_date'])
total_transactions_df['transaction_date_fmt'] = pd.to_datetime(total_transactions_df['transaction_date'])
total_transactions_df.sort_values(
    by=['post_date_fmt', 'transaction_date_fmt', 'amount', 'description'],
    ascending=[True, True, True, True],
    inplace=True
)
total_transactions_df.drop(['post_date_fmt', 'transaction_date_fmt'], axis=1, inplace=True)
total_transactions_df.reset_index(drop=True, inplace=True)

gc = gspread.service_account()
finance_tracker_db_spreadsheet = gc.open_by_key(SPREADSHEET_KEY)
east_west_bank_credit_card_statements_worksheet = finance_tracker_db_spreadsheet.worksheet(WORKSHEET_NAME)
east_west_bank_credit_card_statements_worksheet.update([total_transactions_df.columns.values.tolist()] + total_transactions_df.values.tolist())
# east_west_bank_credit_card_statements_worksheet.format("D:D", {"numberFormat": {"type": "CURRENCY"}})
# east_west_bank_credit_card_statements_worksheet.format("A:B", {"numberFormat": {"type": "DATE_TIME"}})

print("SUCCESS")