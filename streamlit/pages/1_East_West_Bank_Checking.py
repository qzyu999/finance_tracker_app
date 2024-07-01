import streamlit as st
import os
import pandas as pd
import gspread
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.express as px
import plotly.colors as pc
import numpy as np
from datetime import datetime


SPREADSHEET_KEY=os.environ['SPREADSHEET_KEY']
EAST_WEST_BANK_BANK_STATEMENTS_WORKSHEET_NAME='east_west_bank_bank_statements'
EAST_WEST_BANK_BANK_STATEMENTS_CATEGORIZED_WORKSHEET_NAME='east_west_bank_bank_statements_categorized'
EAST_WEST_BANK_BANK_STATEMENT_INITIAL_BALANCE=2459.25

st.set_page_config(layout="wide")

# connect to Google Sheets
gc = gspread.service_account()
finance_tracker_db_spreadsheet = gc.open_by_key(SPREADSHEET_KEY)

# load df
east_west_bank_bank_statements_categorized_worksheet = finance_tracker_db_spreadsheet.worksheet(EAST_WEST_BANK_BANK_STATEMENTS_CATEGORIZED_WORKSHEET_NAME)
east_west_bank_bank_statements_categorized_worksheet_df = pd.DataFrame(east_west_bank_bank_statements_categorized_worksheet.get_all_records())

east_west_bank_balance = EAST_WEST_BANK_BANK_STATEMENT_INITIAL_BALANCE + \
    round(east_west_bank_bank_statements_categorized_worksheet_df.loc[
        ~east_west_bank_bank_statements_categorized_worksheet_df['amount'].isna()
    ]['amount'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum(), 2)

east_west_bank_bank_statements_categorized_worksheet_df['float_amount'] = \
    east_west_bank_bank_statements_categorized_worksheet_df['amount'] \
    .apply(lambda x: float(x.replace('$', '').replace(',', '')))
east_west_bank_bank_statements_categorized_worksheet_df.loc[0, 'float_amount'] += EAST_WEST_BANK_BANK_STATEMENT_INITIAL_BALANCE

east_west_bank_bank_statements_categorized_worksheet_df['float_amount_cumsum'] = east_west_bank_bank_statements_categorized_worksheet_df['float_amount'].cumsum()

st.title('East West Bank Checking')

todays_date = datetime.now()
start, end = st.date_input('Select Date Range', value=(datetime(todays_date.year, 1, 1), todays_date))
start, end = pd.to_datetime(start), pd.to_datetime(end)

east_west_bank_bank_statements_categorized_worksheet_df['transaction_date'] = pd.to_datetime(east_west_bank_bank_statements_categorized_worksheet_df['transaction_date'])
east_west_bank_bank_statements_categorized_worksheet_df = east_west_bank_bank_statements_categorized_worksheet_df.loc[
    (east_west_bank_bank_statements_categorized_worksheet_df['transaction_date'] >= start) &
    (east_west_bank_bank_statements_categorized_worksheet_df['transaction_date'] <= end)
].copy()

cusum_subset = east_west_bank_bank_statements_categorized_worksheet_df['float_amount'].cumsum().values[-1]
col1, col2 = st.columns(2)
col1.metric("Current EWB Balance", f"${east_west_bank_balance:,.2f}")
col2.metric("Balance During Period", f"${cusum_subset:,.2f}")

fig = px.line(
    east_west_bank_bank_statements_categorized_worksheet_df,
    x="transaction_date",
    y="float_amount_cumsum",
    title='Line Plot of Cumulative Sum of Amount',
)
fig.update_layout(xaxis_title="Transaction Date", yaxis_title="Cumulative Sum of Amount ($)")
st.plotly_chart(fig, use_container_width=True)

fig = px.bar(
    east_west_bank_bank_statements_categorized_worksheet_df,
    x='category', y='float_amount', title='Bar Chart of Amount Grouped by Category'
)
fig.update_layout(xaxis_title="Category", yaxis_title="Amount ($)")
st.plotly_chart(fig, use_container_width=True)

east_west_bank_bank_statements_categorized_worksheet_df['transaction_date'] = \
    east_west_bank_bank_statements_categorized_worksheet_df['transaction_date'].apply(lambda x: x.date())

east_west_bank_bank_statements_categorized_worksheet_df['float_amount_cumsum'] = \
    east_west_bank_bank_statements_categorized_worksheet_df['float_amount_cumsum'].apply(lambda x: f"${x:,.2f}")

east_west_bank_bank_statements_categorized_worksheet_df.columns = ['Transaction Date', 'Description', 'Amount', 'Category', 'Float Amount', 'Amount Cumulative Sum']
st.dataframe(east_west_bank_bank_statements_categorized_worksheet_df[['Transaction Date', 'Description', 'Amount', 'Category', 'Amount Cumulative Sum']])