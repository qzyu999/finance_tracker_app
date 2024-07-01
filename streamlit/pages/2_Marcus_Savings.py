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
MARCUS_BANK_STATEMENTS_WORKSHEET_NAME='marcus_bank_statements'

st.set_page_config(layout="wide")

# connect to Google Sheets
gc = gspread.service_account()
finance_tracker_db_spreadsheet = gc.open_by_key(SPREADSHEET_KEY)

# load df
marcus_worksheet = finance_tracker_db_spreadsheet.worksheet(MARCUS_BANK_STATEMENTS_WORKSHEET_NAME)
marcus_worksheet_df = pd.DataFrame(marcus_worksheet.get_all_records())

marcus_balance = round(float(marcus_worksheet_df['balance'].tail(1).values[0].replace('$', '').replace(',', '')), 2)
marcus_worksheet_df['float_balance'] = marcus_worksheet_df['balance'].apply(lambda x: float(x.replace('$', '').replace(',', '')))
marcus_worksheet_df['float_credit_debit'] = marcus_worksheet_df['credit_debit'].apply(lambda x: float(x.replace('$', '').replace(',', '')))

interest_earned = marcus_worksheet_df.loc[
    marcus_worksheet_df['category'] == 'Interest',
    'float_credit_debit'
].sum()

st.title('Marcus Savings')

todays_date = datetime.now()
start, end = st.date_input('Select Date Range', value=(datetime(todays_date.year, 1, 1), todays_date))
start, end = pd.to_datetime(start), pd.to_datetime(end)

marcus_worksheet_df['transaction_date'] = pd.to_datetime(marcus_worksheet_df['transaction_date'])
marcus_worksheet_df = marcus_worksheet_df.loc[
    (marcus_worksheet_df['transaction_date'] >= start) &
    (marcus_worksheet_df['transaction_date'] <= end)
].copy()

interest_earned_during_period = marcus_worksheet_df.loc[
    marcus_worksheet_df['category'] == 'Interest',
    'float_credit_debit'
].sum()

cusum_subset = marcus_worksheet_df['float_credit_debit'].cumsum().values[-1]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Current Marcus Balance", f"${marcus_balance:,.2f}")
col2.metric("Current Interest Earned", f"${interest_earned:,.2f}")
col3.metric("Balance During Period", f"${cusum_subset:,.2f}")
col4.metric("Interest Earned During Period", f"${interest_earned_during_period:,.2f}")

fig = px.line(
    marcus_worksheet_df,
    x="transaction_date",
    y="float_balance",
    title='Line Plot of Cumulative Sum of Credits and Debits',
)
fig.update_layout(xaxis_title="Transaction Date", yaxis_title="Cumulative Sum of Credits and Debits ($)")
st.plotly_chart(fig, use_container_width=True)

fig = px.bar(
    marcus_worksheet_df,
    x='category', y='float_credit_debit', title='Bar Chart of Credits and Debits Grouped by Category'
)
fig.update_layout(xaxis_title="Category", yaxis_title="Credits and Debits ($)")
st.plotly_chart(fig, use_container_width=True)

marcus_worksheet_df.columns = ['Transaction Date', 'Description', 'Balance', 'Credit/Debit', 'Category', 'Float Balance', 'Float Credit/Debit']
st.dataframe(marcus_worksheet_df[['Transaction Date', 'Description', 'Balance', 'Credit/Debit', 'Category']])

