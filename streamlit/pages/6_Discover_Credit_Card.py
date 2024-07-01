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
DISCOVER_CREDIT_CARD_STATEMENTS_WORKSHEET_NAME='discover_credit_card_statements'

st.set_page_config(layout="wide")

# connect to Google Sheets
gc = gspread.service_account()
finance_tracker_db_spreadsheet = gc.open_by_key(SPREADSHEET_KEY)

# load df
discover_credit_card_statements_worksheet = finance_tracker_db_spreadsheet.worksheet(DISCOVER_CREDIT_CARD_STATEMENTS_WORKSHEET_NAME)
discover_credit_card_statements_worksheet_df = pd.DataFrame(discover_credit_card_statements_worksheet.get_all_records())

discover_credit_card_balance = round(discover_credit_card_statements_worksheet_df.loc[
    ~discover_credit_card_statements_worksheet_df['Amount'].isna()
]['Amount'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum(), 2)

discover_credit_card_statements_worksheet_df['float_amount'] = \
    discover_credit_card_statements_worksheet_df['Amount'] \
    .apply(lambda x: float(x.replace('$', '').replace(',', '')))

total_spend = discover_credit_card_statements_worksheet_df.loc[
    discover_credit_card_statements_worksheet_df['float_amount'] > 0,
    'float_amount'
].sum()

discover_credit_card_statements_worksheet_df['float_amount_cumsum'] = \
    discover_credit_card_statements_worksheet_df['float_amount'].cumsum()

st.title('Discover Credit Card')

discover_credit_card_statements_worksheet_df['Trans. Date'] = pd.to_datetime(discover_credit_card_statements_worksheet_df['Trans. Date'])
discover_credit_card_statements_worksheet_df['Post Date'] = pd.to_datetime(discover_credit_card_statements_worksheet_df['Post Date'])

# Define date ranges
date_range_option = st.selectbox(
    'Select Date Range Option',
    ['All Time', 'YTD', 'MTD', 'Last 7 Days']
)
todays_date = datetime.today()
# Initialize start and end date based on the selected option
if date_range_option == 'All Time':
    start_date = discover_credit_card_statements_worksheet_df['Trans. Date'].min()
    end_date = discover_credit_card_statements_worksheet_df['Trans. Date'].max()
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

discover_credit_card_statements_worksheet_df = discover_credit_card_statements_worksheet_df.loc[
    (discover_credit_card_statements_worksheet_df['Trans. Date'] >= start) &
    (discover_credit_card_statements_worksheet_df['Trans. Date'] <= end)
].copy()

discover_credit_card_subset_balance = round(discover_credit_card_statements_worksheet_df.loc[
    ~discover_credit_card_statements_worksheet_df['Amount'].isna()
]['Amount'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum(), 2)

total_spend_subset = discover_credit_card_statements_worksheet_df.loc[
    discover_credit_card_statements_worksheet_df['float_amount'] > 0,
    'float_amount'
].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Current Discover CC Balance", f"${discover_credit_card_balance:,.2f}")
col2.metric("Total Spent", f"${total_spend:,.2f}")
col3.metric("Balance During Period", f"${discover_credit_card_subset_balance:,.2f}")
col4.metric("Total Spent During Period", f"${total_spend_subset:,.2f}")

fig = px.line(
    discover_credit_card_statements_worksheet_df,
    x="Trans. Date",
    y="float_amount_cumsum",
    title='Line Plot of Cumulative Sum of Amount',
)
fig.update_layout(xaxis_title="Transaction Date", yaxis_title="Cumulative Sum of Amount ($)")
st.plotly_chart(fig, use_container_width=True)

purchases = discover_credit_card_statements_worksheet_df.loc[
    discover_credit_card_statements_worksheet_df['float_amount'] > 0
].copy()
purchases['float_amount_cumsum'] = \
    purchases['float_amount'].cumsum()
fig = px.line(
    purchases,
    x="Trans. Date",
    y="float_amount_cumsum",
    title='Line Plot of Cumulative Sum of Purchases',
)
fig.update_layout(xaxis_title="Transaction Date", yaxis_title="Cumulative Sum of Purchase ($)")
st.plotly_chart(fig, use_container_width=True)

fig = px.bar(
    discover_credit_card_statements_worksheet_df,
    x='Category', y='float_amount', title='Bar Chart of Amount Grouped by Category'
)
fig.update_layout(xaxis_title="Category", yaxis_title="Amount ($)")
st.plotly_chart(fig, use_container_width=True)

discover_credit_card_statements_worksheet_df['Post Date'] = \
    discover_credit_card_statements_worksheet_df['Post Date'].apply(lambda x: x.date())
discover_credit_card_statements_worksheet_df['Trans. Date'] = \
    discover_credit_card_statements_worksheet_df['Trans. Date'].apply(lambda x: x.date())

discover_credit_card_statements_worksheet_df['float_amount_cumsum'] = \
    discover_credit_card_statements_worksheet_df['float_amount_cumsum'].apply(lambda x: f"${x:,.2f}")

discover_credit_card_statements_worksheet_df.columns = ['Trans. Date', 'Post Date', 'Description', 'Amount', 'Category', 'float_amount', 'Amount Cumulative Sum']
st.dataframe(discover_credit_card_statements_worksheet_df[['Trans. Date', 'Description', 'Amount', 'Category', 'Amount Cumulative Sum']])