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
ROBINHOOHD_BROKERAGE_WORKSHEET_NAME='robinhood_brokerage_modified'

st.set_page_config(layout="wide")

# connect to Google Sheets
gc = gspread.service_account()
finance_tracker_db_spreadsheet = gc.open_by_key(SPREADSHEET_KEY)

# load df
robinhood_brokerage_worksheet = finance_tracker_db_spreadsheet.worksheet(ROBINHOOHD_BROKERAGE_WORKSHEET_NAME)
robinhood_brokerage_worksheet_df = pd.DataFrame(robinhood_brokerage_worksheet.get_all_records())

st.title('Robinhood Brokerage')

robinhood_brokerage_worksheet_df['Activity Date'] = pd.to_datetime(robinhood_brokerage_worksheet_df['Activity Date'])
robinhood_brokerage_worksheet_df['Process Date'] = pd.to_datetime(robinhood_brokerage_worksheet_df['Process Date'])
robinhood_brokerage_worksheet_df['Settle Date'] = pd.to_datetime(robinhood_brokerage_worksheet_df['Settle Date'])

# Define date ranges
date_range_option = st.selectbox(
    'Select Date Range Option',
    ['All Time', 'YTD', 'MTD', 'Last 7 Days']
)
todays_date = datetime.today()
# Initialize start and end date based on the selected option
if date_range_option == 'All Time':
    start_date = robinhood_brokerage_worksheet_df['Activity Date'].min()
    end_date = robinhood_brokerage_worksheet_df['Activity Date'].max()
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

robinhood_brokerage_worksheet_df = robinhood_brokerage_worksheet_df.loc[
    (robinhood_brokerage_worksheet_df['Activity Date'] >= start) &
    (robinhood_brokerage_worksheet_df['Activity Date'] <= end)
].copy()

robinhood_brokerage_worksheet_df['Activity Date'] = \
    robinhood_brokerage_worksheet_df['Activity Date'].apply(lambda x: x.date())
robinhood_brokerage_worksheet_df['Process Date'] = \
    robinhood_brokerage_worksheet_df['Process Date'].apply(lambda x: x.date())
robinhood_brokerage_worksheet_df['Settle Date'] = \
    robinhood_brokerage_worksheet_df['Settle Date'].apply(lambda x: x.date())
st.dataframe(robinhood_brokerage_worksheet_df)
