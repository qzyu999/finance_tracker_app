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

st.title('East West Bank Checking')
todays_date = datetime.now()
start, end = st.date_input('Select Date Range', value=(datetime(todays_date.year, 1, 1), todays_date))
start, end = pd.to_datetime(start), pd.to_datetime(end)
east_west_bank_bank_statements_categorized_worksheet_df['transaction_date'] = pd.to_datetime(east_west_bank_bank_statements_categorized_worksheet_df['transaction_date'])
east_west_bank_bank_statements_categorized_worksheet_df = east_west_bank_bank_statements_categorized_worksheet_df.loc[
    (east_west_bank_bank_statements_categorized_worksheet_df['transaction_date'] >= start) &
    (east_west_bank_bank_statements_categorized_worksheet_df['transaction_date'] <= end)
].copy()

st.dataframe(east_west_bank_bank_statements_categorized_worksheet_df)