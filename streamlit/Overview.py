import streamlit as st
import os
import pandas as pd
import gspread
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.express as px
import plotly.colors as pc
import numpy as np


SPREADSHEET_KEY=os.environ['SPREADSHEET_KEY']
EAST_WEST_BANK_BANK_STATEMENTS_WORKSHEET_NAME='east_west_bank_bank_statements'
EAST_WEST_BANK_BANK_STATEMENTS_CATEGORIZED_WORKSHEET_NAME='east_west_bank_bank_statements_categorized'
MARCUS_BANK_STATEMENTS_WORKSHEET_NAME='marcus_bank_statements'
EAST_WEST_BANK_CREDIT_CARD_STATEMENTS_WORKSHEET_NAME='east_west_bank_credit_card_statements'
EAST_WEST_BANK_BANK_STATEMENT_INITIAL_BALANCE=2459.25
EAST_WEST_BANK_CREDIT_CARD_INITIAL_BALANCE=1937.56
TARGET_NET_WORTH = 100000

st.set_page_config(layout="wide")

### MAKE SURE TO ADJUST ALL VALUES INCASE THEY HAVE INITIAL VALUES

# connect to Google Sheets
gc = gspread.service_account()
finance_tracker_db_spreadsheet = gc.open_by_key(SPREADSHEET_KEY)

# load dfs
net_worth_worksheet = finance_tracker_db_spreadsheet.worksheet('net_worth')
net_worth_worksheet_df = pd.DataFrame(net_worth_worksheet.get_all_records())

east_west_bank_bank_statements_categorized_worksheet = finance_tracker_db_spreadsheet.worksheet(EAST_WEST_BANK_BANK_STATEMENTS_CATEGORIZED_WORKSHEET_NAME)
east_west_bank_bank_statements_categorized_worksheet_df = pd.DataFrame(east_west_bank_bank_statements_categorized_worksheet.get_all_records())

marcus_worksheet = finance_tracker_db_spreadsheet.worksheet(MARCUS_BANK_STATEMENTS_WORKSHEET_NAME)
marcus_worksheet_df = pd.DataFrame(marcus_worksheet.get_all_records())

robinhood_brokerage_worksheet = finance_tracker_db_spreadsheet.worksheet('robinhood_brokerage_modified')
robinhood_brokerage_worksheet_df = pd.DataFrame(robinhood_brokerage_worksheet.get_all_records())

robinhood_traditional_ira_worksheet = finance_tracker_db_spreadsheet.worksheet('robinhood_traditional_ira_modified')
robinhood_traditional_ira_worksheet_df = pd.DataFrame(robinhood_traditional_ira_worksheet.get_all_records())

east_west_bank_credit_card_statements_worksheet = finance_tracker_db_spreadsheet.worksheet(EAST_WEST_BANK_CREDIT_CARD_STATEMENTS_WORKSHEET_NAME)
east_west_bank_credit_card_statements_worksheet_df = pd.DataFrame(east_west_bank_credit_card_statements_worksheet.get_all_records())

discover_credit_card_statements_worksheet = finance_tracker_db_spreadsheet.worksheet('discover_credit_card_statements')
discover_credit_card_statements_worksheet_df = pd.DataFrame(discover_credit_card_statements_worksheet.get_all_records())

st.title("Personal Finance Tracker Overview")

# get current and previous net worth variables
total_assets = net_worth_worksheet_df.tail(1)['total_assets'].values[0]
total_liabilities = net_worth_worksheet_df.tail(1)['total_liabilities'].values[0]
net_worth = net_worth_worksheet_df.tail(1)['net_worth'].values[0]

### reminder: add the previous values next time
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Assets", total_assets)
col2.metric("Total Liabilities", total_liabilities)
col3.metric("Net Worth", net_worth)
cur_pct = round(
    (float(net_worth.replace('$', '').replace(',', '')) / TARGET_NET_WORTH) * 100,
    2
)
prev_pct = round(
    ((float(net_worth.replace('$', '').replace(',', '')) - 1000) / TARGET_NET_WORTH) * 100,
    2
)
delta_pct = cur_pct - prev_pct
col4.metric(
    f"Progress to: ${TARGET_NET_WORTH:,.2f}",
    str(cur_pct) + '%',
    str(delta_pct) + '%'
)

east_west_bank_balance = EAST_WEST_BANK_BANK_STATEMENT_INITIAL_BALANCE + \
    round(east_west_bank_bank_statements_categorized_worksheet_df.loc[
        ~east_west_bank_bank_statements_categorized_worksheet_df['amount'].isna()
    ]['amount'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum(), 2)
marcus_balance = round(float(marcus_worksheet_df['balance'].tail(1).values[0].replace('$', '').replace(',', '')), 2)

robinhood_brokerage_portfolio_value = robinhood_brokerage_worksheet_df['Latest Portfolio Value'].tail(1).values[0]

robinhood_traditional_ira_worksheet_value = robinhood_traditional_ira_worksheet_df['Latest Portfolio Value'].tail(1).values[0]

east_west_bank_credit_card_balance = round(east_west_bank_credit_card_statements_worksheet_df.loc[
    ~east_west_bank_credit_card_statements_worksheet_df['amount'].isna()
]['amount'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum(), 2)

discover_credit_card_balance = round(discover_credit_card_statements_worksheet_df.loc[
    ~discover_credit_card_statements_worksheet_df['Amount'].isna()
]['Amount'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum(), 2)

st.write('## Assets Breakdown:')

col1, col2, col3, col4 = st.columns(4)
col1.metric("EWB Balance", f"${east_west_bank_balance:,.2f}")
col2.metric("Marcus Balance", f"${marcus_balance:,.2f}")
col3.metric("RH Brokerage Value", f"${robinhood_brokerage_portfolio_value:,.2f}")
col4.metric("RH Trad. IRA Value", f"${robinhood_traditional_ira_worksheet_value:,.2f}")

east_west_bank_bank_statements_categorized_worksheet_df['float_amount'] = \
    east_west_bank_bank_statements_categorized_worksheet_df['amount'] \
    .apply(lambda x: float(x.replace('$', '').replace(',', '')))
east_west_bank_bank_statements_categorized_worksheet_df.loc[0, 'float_amount'] += EAST_WEST_BANK_BANK_STATEMENT_INITIAL_BALANCE

east_west_bank_bank_statements_categorized_worksheet_df['balance'] = \
    east_west_bank_bank_statements_categorized_worksheet_df['float_amount'].cumsum()

marcus_worksheet_df['float_balance'] = marcus_worksheet_df['balance'].apply(lambda x: float(x.replace('$', '').replace(',', '')))

robinhood_brokerage_worksheet_df['Portfolio Value'].replace('', np.nan, inplace=True)
robinhood_brokerage_worksheet_df['Portfolio Value'].ffill(inplace=True)

robinhood_traditional_ira_worksheet_df['Portfolio Value'].replace('', np.nan, inplace=True)
robinhood_traditional_ira_worksheet_df['Portfolio Value'].ffill(inplace=True)

colors = pc.qualitative.Plotly

# Map each source to a color
color_palette = {
    'East West Bank Checking': colors[0],
    'Marcus Savings': colors[1],
    'Robinhood Brokerage': colors[2],
    'Robinhood Traditional IRA': colors[3],
    'East West Bank CC': colors[4],
    'Discover CC': colors[5],
}

fig = make_subplots(rows=2, cols=2)
fig.add_trace(
    go.Scatter(
        name='East West Bank Checking',
        x=east_west_bank_bank_statements_categorized_worksheet_df['transaction_date'].values.tolist(),
        y=east_west_bank_bank_statements_categorized_worksheet_df['balance'].values.tolist(),
        line=dict(color=color_palette['East West Bank Checking'])
    ),
    row=1, col=1
)
fig.add_trace(
    go.Scatter(
        name='Marcus Savings',
        x=marcus_worksheet_df['transaction_date'].values.tolist(),
        y=marcus_worksheet_df['float_balance'].values.tolist(),
        line=dict(color=color_palette['Marcus Savings'])
    ),
    row=1, col=2
)
fig.add_trace(
    go.Scatter(
        name='Robinhood Brokerage',
        x=robinhood_brokerage_worksheet_df['Activity Date'].values.tolist(),
        y=robinhood_brokerage_worksheet_df['Portfolio Value'].values.tolist(),
        line=dict(color=color_palette['Robinhood Brokerage'])
    ),
    row=2, col=1
)
fig.add_trace(
    go.Scatter(
        name='Robinhood Traditional IRA',
        x=robinhood_traditional_ira_worksheet_df['Process Date'].values.tolist(),
        y=robinhood_traditional_ira_worksheet_df['Portfolio Value'].values.tolist(),
        line=dict(color=color_palette['Robinhood Traditional IRA'])
    ),
    row=2, col=2
)
fig.update_layout(
    title="Line Chart of Asset Balances or Portfolio Values over Time (higher is better)",
)
st.plotly_chart(fig, use_container_width=True)

assets = pd.DataFrame({
    'East West Bank Checking': [east_west_bank_balance],
    'Marcus Savings': [marcus_balance],
    'Robinhood Brokerage': [robinhood_brokerage_portfolio_value],
    'Robinhood Traditional IRA': [robinhood_traditional_ira_worksheet_value]
}).T
assets.reset_index(inplace=True)
assets.columns = ['Source', 'Value']

fig = px.pie(
    assets, values='Value', names='Source', title='Pie Chart of Asset Distribution',
    color='Source', color_discrete_map=color_palette)
st.plotly_chart(fig, use_container_width=True)

st.write('## Liabilities Breakdown:')
east_west_bank_credit_card_balance = round(east_west_bank_credit_card_statements_worksheet_df.loc[
    ~east_west_bank_credit_card_statements_worksheet_df['amount'].isna()
]['amount'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum(), 2)

discover_credit_card_balance = round(discover_credit_card_statements_worksheet_df.loc[
    ~discover_credit_card_statements_worksheet_df['Amount'].isna()
]['Amount'].apply(lambda x: float(x.replace('$', '').replace(',', ''))).sum(), 2)

col1, col2 = st.columns(2)
col1.metric("EWB CC Balance", f"${east_west_bank_credit_card_balance:,.2f}")
col2.metric("Discover CC Balance", f"${discover_credit_card_balance:,.2f}")

east_west_bank_credit_card_statements_worksheet_df['float_amount'] = \
    east_west_bank_credit_card_statements_worksheet_df['amount'] \
    .apply(lambda x: float(x.replace('$', '').replace(',', '')))
east_west_bank_credit_card_statements_worksheet_df.loc[0, 'float_amount'] += EAST_WEST_BANK_BANK_STATEMENT_INITIAL_BALANCE

discover_credit_card_statements_worksheet_df['float_amount'] = \
    discover_credit_card_statements_worksheet_df['Amount'] \
    .apply(lambda x: float(x.replace('$', '').replace(',', '')))

fig = make_subplots(rows=1, cols=2)
fig.add_trace(
    go.Scatter(
        name='East West Bank CC',
        x=east_west_bank_credit_card_statements_worksheet_df['transaction_date'].values.tolist(),
        y=east_west_bank_credit_card_statements_worksheet_df['float_amount'].cumsum().values.tolist(),
        line=dict(color=color_palette['East West Bank CC'])
    ),
    row=1, col=1
)
fig.add_trace(
    go.Scatter(
        name='Discover CC',
        x=discover_credit_card_statements_worksheet_df['Trans. Date'].values.tolist(),
        y=discover_credit_card_statements_worksheet_df['float_amount'].cumsum().values.tolist(),
        line=dict(color=color_palette['Discover CC'])
    ),
    row=1, col=2
)
fig.update_layout(
    title="Line Chart of Liabilities over Time (lower is better)"
)
st.plotly_chart(fig, use_container_width=True)

liabilities = pd.DataFrame({
    'East West Bank CC': [east_west_bank_credit_card_balance],
    'Discover CC': [discover_credit_card_balance],
}).T
liabilities.reset_index(inplace=True)
liabilities.columns = ['Source', 'Value']

fig = px.pie(
    liabilities, values='Value', names='Source', title='Pie Chart of Liabilities Distribution',
    color='Source', color_discrete_map=color_palette)
st.plotly_chart(fig, use_container_width=True)