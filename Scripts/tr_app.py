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
from datetime import timedelta 
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
startDay=3
startMonth=5
startYear=2022
startBalance=1252.38
targetPercentGoal=0.03

#File/Location Related

PersonalTransactionDB="PersonalTranscation.pickle"
dataLocation="../Data/"
dbLocation="../DataBase/"
targetsFile="Targets.json"

#Transaction Related
columns_tst=["symbol","qty","buyPrice","sellPrice","pnl","boughtTimestamp","soldTimestamp","duration"]

#Classes

class TargetsCls:

    def __init__(self,ib, pt, nqf, mnqf, sy, sm, sd, excl):
        self._ib=ib
        self._pt=pt
        self._nqf=nqf
        self._mnqf=mnqf
        self._startDate=datetime.datetime(sy, sm, sd).date()
        self._exset=set()
        for dt in excl:
            list1=dt.split("-")
            edt=datetime.datetime(int(list1[2]), int(list1[0]), int(list1[1])).date()
            self._exset.add(edt)

    @property
    def ib(self):
        return self._ib

    @property
    def pt(self):
        return self._pt

    @property
    def nqf(self):
        return self._nqf

    @property
    def mnqf(self):
        return self._mnqf

    @property
    def startDate(self):
        return self._startDate



#Functions

def processTargetsFile():
    targetkeys=list()
    datadict=dict()
    tf=dataLocation+targetsFile
    with open(tf,"r") as f:
        targets=json.load(f)
    for item in targets['Targets']:
        for key in item.keys():
            targetkeys.append(key)
            ib=item[key]['IB']
            pt=item[key]['TGT%']
            nqf=item[key]['NQFee']
            mnqf=item[key]['MNQFee']
            sy=item[key]['SY']
            sm=item[key]['SM']
            sd=item[key]['SD']
            excl=item[key]['Exclusions']
            tcls=TargetsCls(ib, pt, nqf, mnqf, sy, sm, sd, excl)
            datadict[key]=tcls
    return(targetkeys,datadict)

def createSchedule(tcls):
    schedule=dict({"Day":[],"Date":[], "AccountGoal":[], "DailyGoal":[],"CumTargetGoal":[]})
    currDate=tcls.startDate
    count=1
    prev=tcls.ib
    cumTargetGoal=0
    for i in range(60):
        dat=currDate+timedelta(days=i)
        if dat.weekday() < 5:
            temp1=tcls.ib*(pow((1+tcls.pt),float(count)))
            temp11=round(temp1,2)
            schedule["AccountGoal"].append(('%f' % temp11).rstrip('0').rstrip('.'))
            temp2=temp11-prev
            temp22=round(temp2,2)
            schedule["DailyGoal"].append(('%f' % temp22).rstrip('0').rstrip('.'))
            cumTargetGoal+=temp22
            cumTargetGoal1=round(cumTargetGoal,2)
            schedule["CumTargetGoal"].append(('%f' % cumTargetGoal1).rstrip('0').rstrip('.'))
            prev=temp1
            schedule["Day"].append(count)
            count+=1
            #st.write(f"date is :{dat.date()}")
            schedule["Date"].append(dat) 
    df=pd.DataFrame(schedule)
    df.set_index("Day",inplace=True)
    return(df)

def main():
    #Parse Targets File
    (targetkeys,datadict)=processTargetsFile()

    #streamlit code
    st.set_page_config(layout="wide")
    with st.sidebar:
        st.header("Control Panel")
        mode=st.selectbox('Operation Mode',["Setup","Dashboard", "Dataframes","Daily","Calendar", "Charting","Schedule"])

    if mode == "Setup":
        st.header("Configuration")
        st.session_state.selectedTarget=st.radio(f"Working with Target:", targetkeys)
        st.header("DataBase Operations")
        op1=st.radio(f"Working with DB {PersonalTransactionDB}", ("Display","Create","Update"))
        if op1 == "Create":
            st.write("Creating")
        elif op1 == "Update":
            st.write("Updating")
        elif op1 == "Display":
            st.write("Displaying")
    elif mode == "Schedule":
        st.dataframe(createSchedule(datadict[st.session_state.selectedTarget]))

if __name__ == "__main__" or __name__ == "__tr_app__":
    # execute only if run as a script
    main()