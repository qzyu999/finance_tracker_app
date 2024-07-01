import streamlit as st
import os
import pandas as pd
import gspread
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.express as px
import plotly.colors as pc
import numpy as np
from datetime import datetime, timedelta

SPREADSHEET_KEY=os.environ['SPREADSHEET_KEY']
EAST_WEST_BANK_CREDIT_CARD_STATEMENTS_WORKSHEET_NAME='east_west_bank_credit_card_statements'
EAST_WEST_BANK_CREDIT_CARD_INITIAL_BALANCE=1937.56

st.set_page_config(layout="wide")

# connect to Google Sheets
gc = gspread.service_account()
finance_tracker_db_spreadsheet = gc.open_by_key(SPREADSHEET_KEY)

# load df
east_west_bank_credit_card_statements_worksheet = finance_tracker_db_spreadsheet.worksheet(EAST_WEST_BANK_CREDIT_CARD_STATEMENTS_WORKSHEET_NAME)
east_west_bank_credit_card_statements_worksheet_df = pd.DataFrame(east_west_bank_credit_card_statements_worksheet.get_all_records())

east_west_bank_credit_card_balance = round(east_west_bank_credit_card_statements_worksheet_df.loc[
    ~east_west_bank_credit_card_statements_worksheet_df['amount'].isna()
]['amount'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum(), 2)

east_west_bank_credit_card_statements_worksheet_df['float_amount'] = \
    east_west_bank_credit_card_statements_worksheet_df['amount'] \
    .apply(lambda x: float(x.replace('$', '').replace(',', '')))
east_west_bank_credit_card_statements_worksheet_df.loc[0, 'float_amount'] += EAST_WEST_BANK_CREDIT_CARD_INITIAL_BALANCE

total_spend = east_west_bank_credit_card_statements_worksheet_df.loc[
    east_west_bank_credit_card_statements_worksheet_df['float_amount'] > 0,
    'float_amount'
].sum()

east_west_bank_credit_card_statements_worksheet_df['float_amount_cumsum'] = east_west_bank_credit_card_statements_worksheet_df['float_amount'].cumsum()

st.title('East West Bank Credit Card')

east_west_bank_credit_card_statements_worksheet_df['post_date'] = pd.to_datetime(east_west_bank_credit_card_statements_worksheet_df['post_date'])
east_west_bank_credit_card_statements_worksheet_df['transaction_date'] = pd.to_datetime(east_west_bank_credit_card_statements_worksheet_df['transaction_date'])

# Define date ranges
date_range_option = st.selectbox(
    'Select Date Range Option',
    ['All Time', 'YTD', 'MTD', 'Last 7 Days']
)
todays_date = datetime.today()
# Initialize start and end date based on the selected option
if date_range_option == 'All Time':
    start_date = east_west_bank_credit_card_statements_worksheet_df['transaction_date'].min()
    end_date = east_west_bank_credit_card_statements_worksheet_df['transaction_date'].max()
elif date_range_option == 'YTD':
    start_date = datetime(todays_date.year, 1, 1)
    end_date = todays_date
elif date_range_option == 'MTD':
    start_date = datetime(todays_date.year, todays_date.month, 1)
    end_date = todays_date
elif date_range_option == 'Last 7 Days':
    start_date = todays_date - timedelta(days=7)
    end_date = todays_date

# Display date input with the selected range
start, end = st.date_input('Select Date Range', value=(start_date, end_date))
start, end = pd.to_datetime(start), pd.to_datetime(end)

east_west_bank_credit_card_statements_worksheet_df = east_west_bank_credit_card_statements_worksheet_df.loc[
    (east_west_bank_credit_card_statements_worksheet_df['transaction_date'] >= start) &
    (east_west_bank_credit_card_statements_worksheet_df['transaction_date'] <= end)
].copy()

east_west_bank_credit_card_subset_balance = round(east_west_bank_credit_card_statements_worksheet_df.loc[
    ~east_west_bank_credit_card_statements_worksheet_df['amount'].isna()
]['amount'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum(), 2)

total_spend_subset = east_west_bank_credit_card_statements_worksheet_df.loc[
    east_west_bank_credit_card_statements_worksheet_df['float_amount'] > 0,
    'float_amount'
].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Current EWB CC Balance", f"${east_west_bank_credit_card_balance:,.2f}")
col2.metric("Total Spent", f"${total_spend:,.2f}")
col3.metric("Balance During Period", f"${east_west_bank_credit_card_subset_balance:,.2f}")
col4.metric("Total Spent During Period", f"${total_spend_subset:,.2f}")

fig = px.line(
    east_west_bank_credit_card_statements_worksheet_df,
    x="transaction_date",
    y="float_amount_cumsum",
    title='Line Plot of Cumulative Sum of Amount',
)
fig.update_layout(xaxis_title="Transaction Date", yaxis_title="Cumulative Sum of Amount ($)")
st.plotly_chart(fig, use_container_width=True)

purchases = east_west_bank_credit_card_statements_worksheet_df.loc[
    east_west_bank_credit_card_statements_worksheet_df['float_amount'] > 0
].copy()
purchases['float_amount_cumsum'] = \
    purchases['float_amount'].cumsum()
fig = px.line(
    purchases,
    x="transaction_date",
    y="float_amount_cumsum",
    title='Line Plot of Cumulative Sum of Purchases',
)
fig.update_layout(xaxis_title="Transaction Date", yaxis_title="Cumulative Sum of Purchase ($)")
st.plotly_chart(fig, use_container_width=True)

fig = px.bar(
    east_west_bank_credit_card_statements_worksheet_df,
    x='category', y='float_amount', title='Bar Chart of Amount Grouped by Category'
)
fig.update_layout(xaxis_title="Category", yaxis_title="Amount ($)")
st.plotly_chart(fig, use_container_width=True)

east_west_bank_credit_card_statements_worksheet_df['post_date'] = \
    east_west_bank_credit_card_statements_worksheet_df['post_date'].apply(lambda x: x.date())
east_west_bank_credit_card_statements_worksheet_df['transaction_date'] = \
    east_west_bank_credit_card_statements_worksheet_df['transaction_date'].apply(lambda x: x.date())

east_west_bank_credit_card_statements_worksheet_df['float_amount_cumsum'] = \
    east_west_bank_credit_card_statements_worksheet_df['float_amount_cumsum'].apply(lambda x: f"${x:,.2f}")

east_west_bank_credit_card_statements_worksheet_df.columns = ['Post Date', 'Transaction Date', 'Description', 'Amount', 'Date Range', 'Category', 'Float Amount', 'Amount Cumulative Sum']
st.dataframe(east_west_bank_credit_card_statements_worksheet_df[['Transaction Date', 'Description', 'Amount', 'Date Range', 'Category', 'Amount Cumulative Sum']])