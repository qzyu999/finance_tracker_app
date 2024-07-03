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
ROBINHOOHD_OPTIONS_TRADING_WORKSHEET_NAME='robinhood_options_trading'
ROBINHOOHD_OPTIONS_PREMIUM_WORKSHEET_NAME='robinhood_options_premium'

st.set_page_config(layout="wide")

# connect to Google Sheets
gc = gspread.service_account()
finance_tracker_db_spreadsheet = gc.open_by_key(SPREADSHEET_KEY)

# load df
robinhood_brokerage_worksheet = finance_tracker_db_spreadsheet.worksheet(ROBINHOOHD_BROKERAGE_WORKSHEET_NAME)
robinhood_brokerage_worksheet_df = pd.DataFrame(robinhood_brokerage_worksheet.get_all_records())

robinhood_options_trading_worksheet = finance_tracker_db_spreadsheet.worksheet(ROBINHOOHD_OPTIONS_TRADING_WORKSHEET_NAME)
robinhood_options_trading_worksheet_df = pd.DataFrame(robinhood_options_trading_worksheet.get_all_records())

robinhood_options_premium_worksheet = finance_tracker_db_spreadsheet.worksheet(ROBINHOOHD_OPTIONS_PREMIUM_WORKSHEET_NAME)
robinhood_options_premium_worksheet_df = pd.DataFrame(robinhood_options_premium_worksheet.get_all_records())

st.title('Robinhood Brokerage')

robinhood_brokerage_worksheet_df['Activity Date'] = pd.to_datetime(robinhood_brokerage_worksheet_df['Activity Date'])
robinhood_brokerage_worksheet_df['Process Date'] = pd.to_datetime(robinhood_brokerage_worksheet_df['Process Date'])
robinhood_brokerage_worksheet_df['Settle Date'] = pd.to_datetime(robinhood_brokerage_worksheet_df['Settle Date'])

robinhood_brokerage_portfolio_value = robinhood_brokerage_worksheet_df['Latest Portfolio Value'].tail(1).values[0]

total_deposits = robinhood_brokerage_worksheet_df.loc[
    robinhood_brokerage_worksheet_df['Description'] == 'ACH Deposit',
    'Amount'
].sum()
total_withdrawals = robinhood_brokerage_worksheet_df.loc[
    robinhood_brokerage_worksheet_df['Description'] == 'ACH Withdrawal',
    'Amount'
].sum()

total_purchase_sold = robinhood_brokerage_worksheet_df.copy()
total_purchase_sold['Price'] = total_purchase_sold['Price'].replace('', 0)
total_purchase_sold['Quantity'] = total_purchase_sold['Quantity'].replace('', 0)
total_purchase_sold['PQ'] = total_purchase_sold['Price'].astype(float) * \
    total_purchase_sold['Quantity'].astype(float)
total_purchases = total_purchase_sold.loc[
    total_purchase_sold['Trans Code'] == 'Buy',
    'PQ'
].sum()
total_sold = total_purchase_sold.loc[
    total_purchase_sold['Trans Code'] == 'Sell',
    'PQ'
].sum()

total_premium_sold = round(robinhood_options_premium_worksheet_df['Amount'].sum(), 2)

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

col1, col2, col3 = st.columns(3)
col1.metric("RH Brokerage Current Portfolio Value", f"${robinhood_brokerage_portfolio_value:,.2f}")
col2.metric("Total Deposits", f"${total_deposits:,.2f}")
col3.metric("Total Withdrawals", f"${total_withdrawals:,.2f}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Purchases", f"${total_purchases:,.2f}")
col2.metric("Total Sold", f"${total_sold:,.2f}")
col3.metric("PnL", f"${total_sold - total_purchases:,.2f}")
col4.metric("Total Premium Sold", f"${total_premium_sold:,.2f}")

robinhood_brokerage_worksheet_interp = robinhood_brokerage_worksheet_df.copy()
robinhood_brokerage_worksheet_interp['Portfolio Value'].replace('', np.nan, inplace=True)
robinhood_brokerage_worksheet_interp['Portfolio Value'].ffill(inplace=True)
robinhood_brokerage_worksheet_interp['Portfolio Value'] = robinhood_brokerage_worksheet_interp['Portfolio Value'].interpolate()
fig = px.line(
    robinhood_brokerage_worksheet_interp,
    x="Activity Date",
    y="Portfolio Value",
    title='Line Plot of Portfolio Value (with interpolation)',
)
fig.update_layout(xaxis_title="Activity Date", yaxis_title="Portfolio Value ($)")
st.plotly_chart(fig, use_container_width=True)

price_quantity = robinhood_brokerage_worksheet_df.copy()
price_quantity.loc[
    price_quantity['Trans Code'] == 'Sell',
    'Price'
] *= -1
price_quantity['Price'] = price_quantity['Price'].replace('', 0)
price_quantity['Quantity'] = price_quantity['Quantity'].replace('', 0)
price_quantity['PriceQuantity'] = price_quantity['Price'].astype(float) * price_quantity['Quantity'].astype(float)
price_quantity = price_quantity.loc[
    (price_quantity['PriceQuantity'] != '') &
    (~price_quantity['PriceQuantity'].isna())
]
fig = px.bar(
    price_quantity,
    x='Instrument', y='PriceQuantity', title='Bar Chart of Price * Quantity Grouped by Stock'
)
fig.update_layout(xaxis_title="Category", yaxis_title="Amount ($)")
st.plotly_chart(fig, use_container_width=True)

instrument_buys = robinhood_brokerage_worksheet_df.loc[robinhood_brokerage_worksheet_df['Trans Code'] == 'Buy', ['Instrument', 'Quantity']]
instrument_buys = instrument_buys.groupby('Instrument')['Quantity'].sum().reset_index()

fig = px.pie(instrument_buys, values='Quantity', names='Instrument', title='Pie Chart of Quantity of Stocks Purchased')
st.plotly_chart(fig, use_container_width=True)

instrument_sells = robinhood_brokerage_worksheet_df.loc[robinhood_brokerage_worksheet_df['Trans Code'] == 'Sell', ['Instrument', 'Quantity']]
instrument_sells = instrument_sells.groupby('Instrument')['Quantity'].sum().reset_index()

fig = px.pie(instrument_sells, values='Quantity', names='Instrument', title='Pie Chart of Quantity of Stocks Sold')
st.plotly_chart(fig, use_container_width=True)

st.dataframe(robinhood_brokerage_worksheet_df)
