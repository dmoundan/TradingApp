#!/usr/bin/env python

import streamlit as st
import plotly.express as px 
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import argparse
import sys
import os
import pandas as pd
import numpy as np 
import datetime
from dateutil.relativedelta import relativedelta, FR
import calendar
import matplotlib.pyplot as plt
import json

from collections import deque

import yfinance as yf


def process_df(df):
    list1=list()
    for row in df.itertuples(index=False):
        l1=row[5].split(" ")
        l11=l1[0].split("/")
        l12=l1[1].split(":")
        dt1=datetime.datetime(int(l11[2]), int(l11[0]), int(l11[1]),int(l12[0]),int(l12[1]), int(l12[2]))
        l2=row[6].split(" ")
        l21=l2[0].split("/")
        l22=l2[1].split(":")
        dt2=datetime.datetime(int(l21[2]), int(l21[0]), int(l21[1]),int(l22[0]),int(l22[1]), int(l22[2]))
        l3=l1[1].split(":")
        if dt1 < dt2:
            tp="Long"
            starttime=row[5]
            endtime=row[6]
        else:
            tp="Short"
            starttime=row[6]
            endtime=row[5]
        tdict=dict({"Quantity":row[1],"Type":tp, "BuyPrice": row[2], "SellPrice": row[3], "StartTime": starttime, "EndTime":endtime, "Symbol":row[0]})            
        list1.append(tdict)
    result=pd.DataFrame(list1)   
    return result


######Globals########

#File/Location Related

PersonalTransactionDB="PersonalTranscation.pickle"
dataLocation="../Data/"
dbLocation="../DataBase/"
targetsFile="Targets.json"

#Transaction Related
columns_tst=["symbol","qty","buyPrice","sellPrice","pnl","boughtTimestamp","soldTimestamp","duration"]

def main():
    #streamlit code
    st.set_page_config(layout="wide")
    with st.sidebar:
        st.header("Control Panel")
        mode=st.selectbox('Operation Mode',["DataBase","Dashboard", "Dataframes","Daily","Calendar", "Charting"])

    if mode == "DataBase":
        st.header("DataBase Operations")
        op1=st.radio(f"Working with DB {PersonalTransactionDB}", ("Display","Create","Update"))
        if op1 == "Create":
            st.write("Creating")
        elif op1 == "Update":
            st.write("Updating")
        elif op1 == "Display":
            st.write("Displaying")


if __name__ == "__main__" or __name__ == "__tr_app__":
    # execute only if run as a script
    main()