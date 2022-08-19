#!/usr/bin/env python

from tracemalloc import start
from argon2 import PasswordHasher
import streamlit as st
import plotly.express as px 
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import argparse
import sys
import os
import csv

import pandas as pd
import numpy as np 
import datetime
from datetime import timedelta 
from dateutil.relativedelta import relativedelta, FR
import calendar
import matplotlib.pyplot as plt
import json
import pickle


from collections import deque

import yfinance as yf

import requests
from bs4 import BeautifulSoup
import lxml
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

######Globals########

#File/Location Related
DRIVER_PATH="/Users/dinos/Development/Trading/TradingApp/Executables/chromedriver"

PersonalTransactionDB="PersonalTranscation.pickle"
dataLocation="../Data/"
dbLocation="../DataBase/"
targetsFile="Targets.json"

weeklyOptions="weeklys.csv"
xletfs="XLETFs.json"
wpf="weeklies.pickle"
icpf="ic.pickle"
xletfpf="xletf.pickle"

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

    @property
    def exset(self):
        return self._exset


class ProcessTrades:

    def __init__(self, df):
        self._full_df=df
        self._days_dict=dict()
        self._daily_df=pd.DataFrame()
        self._summary_df=pd.DataFrame()
        self._summary_df_2=pd.DataFrame()
        self._summary_df_3=pd.DataFrame()

    @property
    def summary_df(self):
        return self._summary_df

    @property
    def summary_df_2(self):
        return self._summary_df_2

    @property
    def summary_df_3(self):
        return self._summary_df_3
        
    @property
    def daily_df(self):
        return self._daily_df

    def create_summary_df(self,tc):
        fees=0
        trades=0
        net=0
        longs=0
        shorts=0
        points=0
        w20s=0
        winners=0
        losers=0
        long_winners=0
        short_winners=0
        win_points=0
        loss_points=0
        largest_winner=0
        largest_loser=0
        for row in self._full_df.itertuples(index=False):
            if "MNQ" in row[6]:
                fees+=tc.mnqf
            else:
                fees+=tc.nqf    
            trades+=1
            st=self.__calctime(row[4])
            et=self.__calctime(row[5])
            if row[1] == "Long":
                if "MNQ" in row[6]:
                    net+=2.0*(row[3]-row[2])
                else:
                    net+=20.0*(row[3]-row[2])
                longs+=1
                points+= row[3]-row[2]
                if row[3] > row[2]:
                    if (et-st).total_seconds() >= 20:
                        w20s+=1
                    winners+=1
                    long_winners+=1
                    t1=row[3]-row[2]
                    win_points+=t1
                    if t1 > largest_winner:
                        largest_winner=round(t1,2)
                else:
                    losers+=1
                    t2=abs(row[3]-row[2])
                    loss_points+=t2
                    if t2 > largest_loser:
                        largest_loser=round(t2,2)
            else:
                if "MNQ" in row[6]:
                    net+=2.0*(row[3]-row[2])
                else:
                    net+=20.0*(row[3]-row[2])
                shorts+=1
                points+= row[3]-row[2]
                if row[3] > row[2]:
                    if (et-st).total_seconds() >= 20:
                        w20s+=1
                    winners+=1
                    short_winners+=1
                    t1=row[3]-row[2]
                    win_points+=t1
                    if t1 > largest_winner:
                        largest_winner=round(t1,2)
                else:
                    losers+=1
                    t2=abs(row[3]-row[2])
                    loss_points+=t2
                    if t2 > largest_loser:
                        largest_loser=round(t2,2)
        tdict=dict()
        tdict["Trades"]=[trades]
        tdict["Winners"]=[winners]
        tdict["Losers"]=[losers]
        tdict["Win%"]= ('%f' % round((winners/trades)*100,2)).rstrip('0').rstrip('.')
        tdict["Net"]=[net-fees]
        tdict["Fees$"]=[fees]
        tdict["NQNet"]=[ ('%f' % (points*20.0-trades*tc.nqf)).rstrip('0').rstrip('.')]
        tdict["NQFees$"]=[('%f' % (trades*tc.nqf)).rstrip('0').rstrip('.')]
        
        if winners > 0:
            avg_winner=round(win_points/winners,2)
        #    tdict["AWinP"]=[avg_winner]
        if losers > 0:
            avg_loser=round(loss_points/losers,2)
        #    tdict["ALosP"]=[avg_loser]
        if winners > 0 and losers > 0:
            tdict["Ri/Re"]=[round(avg_loser/avg_winner,2)]
        else:
            tdict["Ri/Re"]=[0]
        tdict["Win20s"]=[w20s]
        if winners > 0:
            tdict["Win20s%"]=[('%f' % round((w20s/winners)*100,2)).rstrip('0').rstrip('.')]

        tdict1=dict()
        tdict1["AvgTr"]=[round(trades/len(self._days_dict),2)]
        tdict1["AvgNet"]=[round((net-fees)/len(self._days_dict),2)]
        tdict1["AvgFees"]=[round(fees/len(self._days_dict),2)]
        tdict1["AvgNQNet"]=[ ('%f' % (round((points*20.0-trades*tc.nqf)/len(self._days_dict),2))).rstrip('0').rstrip('.')]
        tdict1["AvgNQFees$"]=[('%f' % (round(trades*tc.nqf/len(self._days_dict),2))).rstrip('0').rstrip('.')]
        
        tdict1["LWin"]=[largest_winner]
        tdict1["LLoss"]=[largest_loser]
        if winners > 0:
            tdict1["AWin"]=[avg_winner]
        if losers > 0:
            tdict1["ALoss"]=[avg_loser]

        tdict2=dict()
        tdict2["Shorts"]=[shorts]
        tdict2["ShWins"]=[short_winners]
        if shorts !=0:
            tdict2["ShWin%"]= ('%f' % round((short_winners/shorts)*100,2)).rstrip('0').rstrip('.')
        else:
            tdict2["ShWin%"]=0
        tdict2["Longs"]=[longs]
        tdict2["LWins"]=[long_winners]
        if longs != 0:
            tdict2["LWin%"]= ('%f' % round((long_winners/longs)*100,2)).rstrip('0').rstrip('.')
        else:
            tdict2["LWin%"]=0
        self._summary_df=pd.DataFrame(tdict)
        self._summary_df_2=pd.DataFrame(tdict1)
        self._summary_df_3=pd.DataFrame(tdict2)

    def __separate_days(self):
        for row in self._full_df.itertuples(index=False):
            l1=row[4].split(" ")
            tl=l1[0].replace("/","-")
            l2=tl.split("-")
            dt=datetime.datetime(int(l2[2]), int(l2[0]), int(l2[1]))
            l3=l1[1].split(":")
            if int(l3[0]) >= 17:  #Here we are considering transactions after 17:00:00 CST to be part of next day
                dt1=dt.date()+datetime.timedelta(days=1)
            else:
                dt1=dt.date()
            points=row[3]-row[2]
            tdict=dict({"Quantity":[row[0]],"Type":[row[1]], "BuyPrice": [row[2]], "SellPrice": [row[3]], "StartTime": [row[4]], "EndTime":[row[5]], "Symbol":[row[6]], "Points":[points]})            

            if dt1 in self._days_dict:
                points=row[3]-row[2]
                tdict=dict({"Quantity":[row[0]],"Type":[row[1]], "BuyPrice": [row[2]], "SellPrice": [row[3]], "StartTime": [row[4]], "EndTime":[row[5]], "Symbol":[row[6]], "Points":[points]})            
                self._days_dict[dt1]=self._days_dict[dt1].append(pd.DataFrame(tdict), ignore_index=False)
            else:
                self._days_dict[dt1]=pd.DataFrame(tdict)
            tdict.clear()

    def __calctime(self, data):
        l1=data.split(" ")
        tl=l1[0].replace("/","-")
        l11=tl.split("-")
        l12=l1[1].split(":")
        st=datetime.datetime(int(l11[2]),int(l11[0]),int(l11[1]),int(l12[0]),int(l12[1]),int(l12[2]))
        return st

    def __validate(self,dt,tc):
        contracts=0
        points=0
        winners=0
        losers=0
        longs=0
        shorts=0
        long_winners=0
        short_winners=0
        win_points=0
        loss_points=0
        largest_winner=0
        largest_loser=0
        w20s=0
        fees=0
        net=0
        #fee=TradeFee
        global point_value
        for row in self._days_dict[dt].itertuples(index=False):
            if "MNQ" in row[6]:
                point_value=2.0
                fees+=tc.mnqf
            else:
                point_value=20.0
                fees+=tc.nqf
            contracts+=1
            st=self.__calctime(row[4])
            """
            starttime=row[4]
            l1=starttime.split(" ")
            tl=l1[0].replace("/","-")
            l11=tl.split("-")
            l12=l1[1].split(":")
            st=datetime.datetime(int(l11[2]),int(l11[0]),int(l11[1]),int(l12[0]),int(l12[1]),int(l12[2]))
            endtime=row[5]
            l2=endtime.split(" ")
            tl=l2[0].replace("/","-")
            l21=tl.split("-")
            l22=l2[1].split(":")
            et=datetime.datetime(int(l21[2]),int(l21[0]),int(l21[1]),int(l22[0]),int(l22[1]),int(l22[2]))
            """
            et=self.__calctime(row[5])
            if row[1] == "Long":
                if "MNQ" in row[6]:
                    net+=2.0*(row[3]-row[2])
                else:
                    net+=20.0*(row[3]-row[2])
                longs+=1
                points+= row[3]-row[2]
                if row[3] > row[2]:
                    if (et-st).total_seconds() >= 20:
                        w20s+=1
                    winners+=1
                    long_winners+=1
                    t1=row[3]-row[2]
                    win_points+=t1
                    if t1 > largest_winner:
                        largest_winner=round(t1,2)
                else:
                    losers+=1
                    t2=abs(row[3]-row[2])
                    loss_points+=t2
                    if t2 > largest_loser:
                        largest_loser=round(t2,2)
            else:
                if "MNQ" in row[6]:
                    net+=2.0*(row[3]-row[2])
                else:
                    net+=20.0*(row[3]-row[2])
                shorts+=1
                points+= row[3]-row[2]
                if row[3] > row[2]:
                    if (et-st).total_seconds() >= 20:
                        w20s+=1
                    winners+=1
                    short_winners+=1
                    t1=row[3]-row[2]
                    win_points+=t1
                    if t1 > largest_winner:
                        largest_winner=round(t1,2)
                else:
                    losers+=1
                    t2=abs(row[3]-row[2])
                    loss_points+=t2
                    if t2 > largest_loser:
                        largest_loser=round(t2,2)
        tdict=dict()
        #if not full_df:
        tdict["Date"]=[dt]
        tdict["Trades"]=[contracts]
        tdict["Winners"]=[winners]
        tdict["Losers"]=[losers]
        tdict["Win%"]= ('%f' % round((winners/contracts)*100,2)).rstrip('0').rstrip('.')
        #tdict["Net"]=round(points*point_value-contracts*fee,2)
        tdict["Long"]=[longs]
        #tdict["LongW"]=[long_winners]
        tdict["Short"]=[shorts]
        #tdict["ShortW"]=[short_winners]
        #tdict["Points"]=round(points,2)
        tdict["Net"]=[ ('%f' % (net-fees)).rstrip('0').rstrip('.')]
        tdict["Fees$"]=[ ('%f' % fees).rstrip('0').rstrip('.')]
        tdict["NQNet"]=[ ('%f' % (points*20.0-contracts*tc.nqf)).rstrip('0').rstrip('.')]
        tdict["NQFees$"]=[('%f' % (contracts*tc.nqf)).rstrip('0').rstrip('.')]
        #tdict["Fees%"]=round(((contracts*fee)/(abs(points)*point_value))*100,2)
        if winners > 0:
            avg_winner=round(win_points/winners,2)
        #    tdict["AWinP"]=[avg_winner]
        if losers > 0:
            avg_loser=round(loss_points/losers,2)
        #    tdict["ALosP"]=[avg_loser]
        if winners > 0 and losers > 0:
            tdict["Ri/Re"]=[round(avg_loser/avg_winner,2)]
        else:
            tdict["Ri/Re"]=[0]
        #tdict["LWinP"]=[largest_winner]
        #tdict["LLosP"]=[largest_loser]
        #tdict["Exp$"]=[round(points/contracts,2)*point_value]
        tdict["Win20s"]=[w20s]
        #tdict["WPoints"]=[win_points]
        #tdict["LPoints"]=[loss_points]

        if winners > 0:
            tdict["Win20s%"]=[('%f' % round((w20s/winners)*100,2)).rstrip('0').rstrip('.')]
        result_df=pd.DataFrame(tdict)
        return result_df

    def process_full_df(self, tc):
        self.__separate_days()
        count=0
        count_list=list()
        for key in self._days_dict.keys():
            count+=1
            count_list.append(count)
            self._daily_df=self._daily_df.append(self.__validate(key,tc), ignore_index=True)
        self._daily_df.sort_values(by=['Date'], ascending=True, inplace=True)
        self._daily_df.reset_index(drop=True, inplace=True)
        """
        result_df["Count"]=count_list
        result_df['CumNet']=result_df['Net'].cumsum()
        result_df["CumDailyAvg"]=result_df['CumNet']/result_df['Count']
        if self.platform == "personal":
            result_df["DayROI"]=result_df['Net']
            result_df["DayROI"]=result_df["DayROI"].apply(lambda x: round((x/InitialBalance)*100,2))
            result_df["CumROI"]=result_df['Net'].cumsum()
            result_df["CumROI"]=result_df["CumROI"].apply(lambda x: round((x/InitialBalance)*100,2))
        full_result_df=self.__validate(datetime.datetime(2021,1,1),self.full_df,True)
        return(result_df,full_result_df, days_dict)
        """

#def cal_month(self, month, year, df):
def cal_month(month, year,df):   
    dts=set(df['Date'].tolist())

    obj = calendar.Calendar()
    st.header(f"{calendar.month_name[month]} {year}")
    cols=st.columns(7)
    for j in range (0,7):
        with cols[j]:
            st.write(calendar.day_abbr[j])
    for week in obj.monthdays2calendar(year, month):
        cols=st.columns(7)
        for j in range (len(week)):
            with cols[j]:
                if week[j][0] != 0:
                    dt=datetime.datetime(int(year), int(month),int(week[j][0]))
                    #st.write(f"{week[j][0]}")
                    if dt.date() in dts:
                        row=df[df['Date']==dt.date()]
                        st.metric(f"{row.iloc[0]['Win%']}%",f"{week[j][0]}",row.iloc[0]['Net'])
                    else:
                        st.metric("",f"{week[j][0]}")
    st.session_state.press=False



#Functions

#Highlighting

def custom_style_schedule(row):
    color='white'
    if row.values[8] != "NA":
        if float(row.values[8]) >= (datadict[st.session_state.selectedTarget].pt)*100:
            color = '#bff799'
        elif float(row.values[8]) < (datadict[st.session_state.selectedTarget].pt)*100 and float(row.values[8]) >0:
            color='#f7cb94'
        else:
            color='#faab89'
    return ['background-color: %s' % color]*len(row.values)

def custom_style_result(row):
    color='white'
    if float(row.values[7]) > 0:
        color = '#bff799'
    else:
        color='#faab89'
    return ['background-color: %s' % color]*len(row.values)

def custom_style_result_week(row):
    color='white'
    if float(row.values[2]) > 0:
        color = '#bff799'
    else:
        color='#faab89'
    return ['background-color: %s' % color]*len(row.values)

####Figures
#stacked bar
def fig_stacked_bar(df, lst, title,colors):
    cdm=dict()
    cnt=0
    for item in lst:
        cdm[item]=colors[cnt]
        cnt+=1
    fig = px.bar(df, x='Date', y=lst, title=title,
    #                color_discrete_map={
    #                    lst[0]:"green",
    #                    lst[1]:"red"
    #                }
                    color_discrete_map=cdm
                    )
    fig.update_xaxes(
            rangebreaks=[
                { 'pattern': 'day of week', 'bounds': [6, 1]}
            ]
    )  
    st.write(fig)

#line
def fig_line(df,lst,title):
    fig = px.line(df, x="Date", y=lst, title=title, markers=True)
    fig.update_xaxes(
                    rangebreaks=[
                    { 'pattern': 'day of week', 'bounds': [6, 1]}
                ]
    )  
    st.write(fig)

#Period results and PnL line
def fig_combo(df):
    df1=df
    fig = make_subplots(1,1)
    
    fig.add_trace(go.Bar(x=df['Date'], y=df['Net'],
                    name='Net',
                    marker_color = df['Color'],
                    opacity=0.4,
                    marker_line_color='rgb(8,48,107)',
                    marker_line_width=2),
            row = 1, col = 1)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['CumNet'], line=dict(color='blue'), name='CumNet'),
            row = 1, col = 1)    
    fig.update_xaxes(
            rangebreaks=[
                { 'pattern': 'day of week', 'bounds': [6, 1]}
            ]
    )  
    st.write(fig)

def next_month(month,year, options):
    st.session_state.press=True
    if month < 12:
        st.session_state.selectedMonth+=1
    else:
        if year+1 in options:
            st.session_state.selectedYear+=1
            st.session_state.selectedMonth=1
    


def prev_month(month,year, options):
    st.session_state.press=True
    if month > 1:
        st.session_state.selectedMonth-=1
    else:
        if year-1 in options:
            st.session_state.selectedYear-=1
            st.session_state.selectedMonth=12
    

def processTargetsFile():
    targetkeys=list()
    datadict1=dict()
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
            datadict1[key]=tcls
    return(targetkeys,datadict1)

def createSchedule(tcls, df):
    dts=set(df['Date'].tolist())
    schedule=dict({"Day":[],"Date":[], "AccountGoal":[], "DailyGoal":[],"AdjGoal":[],"CumTargetGoal":[], "DailyResult":[],"CumReturn%":[],"ActualAccount":[],"DailyReturn%":[],"CumActualResult":[],"AheadBehind":[]})
    currDate=tcls.startDate
    count=1
    prev=tcls.ib
    cumTargetGoal=0
    cumActualResult=0
    actualAcct=tcls.ib
    agc=0
    for i in range(60):
        dat=currDate+timedelta(days=i)
        if dat.weekday() < 5 and dat not in tcls.exset:
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
            year=dat.year
            month=dat.month
            day=dat.day
            dt=datetime.datetime(int(year), int(month),int(day))
            
            if dt.date() in dts:
                row=df[df['Date']==dat]
                #print(row.iloc[0]['Net'])
                schedule["DailyResult"].append(row.iloc[0]['Net'])
                dailyreturn=round((float(row.iloc[0]['Net'])/actualAcct)*100,2)
                schedule["DailyReturn%"].append(('%f' % dailyreturn).rstrip('0').rstrip('.'))
                adjgoal=round(tcls.pt*actualAcct,2)
                schedule["AdjGoal"].append(('%f' % adjgoal).rstrip('0').rstrip('.'))
                actualAcct+=float(row.iloc[0]['Net'])
                cumActualResult+=float(row.iloc[0]['Net'])
                cumActualResult1=round(cumActualResult,2)
                actualAcct1=round(actualAcct,2)
                cumreturn=round((cumActualResult1/tcls.ib)*100,2)
                schedule["ActualAccount"].append(('%f' % actualAcct1).rstrip('0').rstrip('.'))
                schedule["CumActualResult"].append(('%f' % cumActualResult1).rstrip('0').rstrip('.'))
                schedule["AheadBehind"].append(('%f' % (cumActualResult1-cumTargetGoal1)).rstrip('0').rstrip('.'))
                schedule["CumReturn%"].append(('%f' % cumreturn).rstrip('0').rstrip('.'))
            else:
                agc+=1
                schedule["DailyResult"].append("NA")
                schedule["ActualAccount"].append("NA")
                schedule["CumActualResult"].append("NA")
                schedule["AheadBehind"].append("NA")
                schedule["CumReturn%"].append("NA")
                schedule["DailyReturn%"].append("NA")
                if agc==1:
                    agt=round(float(schedule["ActualAccount"][-2])*tcls.pt,2)
                    schedule["AdjGoal"].append(('%f' % agt).rstrip('0').rstrip('.'))
                else:
                    schedule["AdjGoal"].append("NA")

            #st.write(f"date is :{dat.date()}")
            schedule["Date"].append(dat) 
    df=pd.DataFrame(schedule)
    df.set_index("Day",inplace=True)
    return(df)

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

def fill_missing_days(weeks, month, year):
    rl=list()
    c1=0
    c2=0
    if weeks[0] == 0: #beginning of month
        for i in weeks:
            if i != 0:
                break
            else:
                c1+=1
    elif weeks[-1] == 0: #end of month
        for i in weeks:
            if i != 0:
                continue
            else:
                c2+=1
    if c2 != 0:
        nday=1
        for i in weeks:
            if i!=0:
                if month > 9:
                    dt=f"{year}-{month}-{i}"
                else:
                    dt=f"{year}-0{month}-{i}"
                rl.append(dt)
            else:
                if month < 12:
                    nmonth=month+1
                    nyear=year
                else:
                    nmonth=1
                    nyear=year+1
                if nmonth > 9:
                    dt=f"{nyear}-{nmonth}-{nday}"
                else:
                    dt=f"{nyear}-0{nmonth}-{nday}"
                nday+=1
                rl.append(dt)
    return rl

def get_weekly_result_df(ddf):
    dts=set(ddf['Date'].tolist())
    sd=datadict[st.session_state.selectedTarget].startDate
    start_year=sd.year
    start_month=sd.month
    start_day=sd.day
    cnow=datetime.datetime.now()
    end_year=cnow.year
    #print(end_year)
    end_month=cnow.month
    #print(end_month)
    end_day=cnow.day
    #print(end_day)
    weekdaynum=calendar.weekday(end_year,end_month,end_day)
    check=set()

    count=0
    week_number=1
    flag=False
    fill_flag=False
    c = calendar.Calendar()
    tdict=dict({"Week" :[], "WeekRange" :[], "Net":[], "AvgNet":[], "Trades":[], "Win%":[],"ActiveDays":[],"Winners":[], "Losers":[]})
    #tdict=dict({"Week" :[], "WeekRange" :[], "Net":[], "Trades":[], "Win%":[],"ActiveDays":[],"Winners":[], "Losers":[], "Ri/Re":[], "Exp$":[], "AWinP":[], "ALosP":[]})

    for year in range(start_year,end_year+1,1):
        smonth=start_month if year <= start_year else 1
        emonth=12 if year != end_year else end_month
        for month in range(smonth, emonth+1,1):
            #print(f"month top {month}")
            if 1 in check and end_day in check and month == end_month:
                #print("in here")
                break
            for weeks in c.monthdayscalendar(year, month):
                #print("====")
                #print(weeks)
                check.clear()
                if fill_flag==True:
                    fill_flag=False
                    #print("+++")
                    #print(weeks)
                    continue
                lofdates=list()
                if start_day in weeks:
                    flag = True
                if flag == True:
                    if weeks[0] != 0:
                        tdict["Week"].append(week_number)
                        if 0 not in weeks:
                            tdict["WeekRange"].append(f"{year}-{month}-{weeks[0]}  --  {year}-{month}-{weeks[4]}")
                            if month < 10:
                                lofdates=[f"{year}-0{month}-{weeks[0]}", f"{year}-0{month}-{weeks[1]}",f"{year}-0{month}-{weeks[2]}",f"{year}-0{month}-{weeks[3]}",f"{year}-0{month}-{weeks[4]}"]
                            else:
                                lofdates=[f"{year}-{month}-{weeks[0]}", f"{year}-{month}-{weeks[1]}",f"{year}-{month}-{weeks[2]}",f"{year}-{month}-{weeks[3]}",f"{year}-{month}-{weeks[4]}"]
                        else:
                            l1=fill_missing_days(weeks,month, year)
                            fill_flag=True
                            tdict["WeekRange"].append(f"{l1[0]}  --  {l1[4]}")
                            lofdates.append(l1[0])
                            lofdates.append(l1[1])
                            lofdates.append(l1[2])
                            lofdates.append(l1[3])
                            lofdates.append(l1[4])
                        week_number+=1
                    else:
                        if count > 0:
                            continue
                        else:
                            tdict["Week"].append(week_number)
                            if 0 not in weeks:
                                tdict["WeekRange"].append(f"{year}-{month}-{weeks[0]}  --  {year}-{month}-{weeks[4]}")
                                if month < 10:
                                    lofdates=[f"{year}-0{month}-{weeks[0]}", f"{year}-0{month}-{weeks[1]}",f"{year}-0{month}-{weeks[2]}",f"{year}-0{month}-{weeks[3]}",f"{year}-0{month}-{weeks[4]}"]
                                else:
                                    lofdates=[f"{year}-{month}-{weeks[0]}", f"{year}-{month}-{weeks[1]}",f"{year}-{month}-{weeks[2]}",f"{year}-{month}-{weeks[3]}",f"{year}-{month}-{weeks[4]}"]
                            else:
                                l1=fill_missing_days(weeks,month, year)
                                fill_flag=True
                                tdict["WeekRange"].append(f"{l1[0]}  --  {l1[4]}")
                                lofdates.append(l1[0])
                                lofdates.append(l1[1])
                                lofdates.append(l1[2])
                                lofdates.append(l1[3])
                                lofdates.append(l1[4])
                            week_number+=1
                    net=0
                    trades=0
                    winners=0
                    losers=0
                    wpoints=0
                    lpoints=0
                    points=0
                    activedays=0
                    for dt in lofdates:
                        #print(dt)
                        l2=dt.split("-") 
                        check.add(int(l2[2]))
                        dt1=datetime.datetime(int(l2[0]),int(l2[1]),int(l2[2]))
                        if dt1.date() in dts:
                            row=ddf[ddf['Date']==dt1.date()]
                            net+=float(row.iloc[0]['Net'])
                            trades+=int(row.iloc[0]['Trades'])
                            winners+=int(row.iloc[0]['Winners'])
                            losers+=int(row.iloc[0]['Losers'])
                            #wpoints+=row.iloc[0]['WPoints'] 
                            #lpoints+=row.iloc[0]['LPoints']
                            #points+=row.iloc[0]['Points']
                            activedays+=1
                    #arisk=lpoints/losers if losers > 0 else 0
                    #areward=wpoints/winners if winners > 0 else 0
                    tdict['Net'].append(net)
                    tdict['Trades'].append(trades)
                    tdict['Winners'].append(winners)
                    tdict['Losers'].append(losers)
                    if trades > 0:
                        tdict['Win%'].append(round((winners/trades)*100,2))
                    else:
                        tdict['Win%'].append(0)
                    tdict['ActiveDays'].append(activedays)
                    if activedays > 0:   
                        tdict['AvgNet'].append(round((net/activedays),2))
                    else:
                        tdict['AvgNet'].append(0)
                    #tdict['Ri/Re'].append(round(arisk/areward,2))
                    #tdict["Exp$"].append(round(points/trades,2)*point_value)
                    #tdict["AWinP"].append(round(wpoints/winners,2))
                    #tdict["ALosP"].append(round(lpoints/losers,2))

                count+=1
                #print(check)
                #print(f"month {month}")
                lastFriday = datetime.datetime.now() + relativedelta(weekday=FR(-1))
                if (end_day in check or ((weekdaynum==5 or weekdaynum==6)and lastFriday.day in check)) and (month==end_month):
                    break
        
    rdf=pd.DataFrame(tdict)
    return rdf


def get_monthly_result_df(ddf):
    dts=set(ddf['Date'].tolist())
    sd=datadict[st.session_state.selectedTarget].startDate
    start_year=sd.year
    start_month=sd.month
    cnow=datetime.datetime.now()
    end_year=cnow.year
    end_month=cnow.month
    month_number=0
    tdict=dict({"Month" :[], "MonthName" :[], "Net":[], "AvgNet":[],"Trades":[], "Win%":[],"ActiveDays":[],"Winners":[], "Losers":[]})
    #tdict=dict({"Month" :[], "MonthName" :[], "Net":[], "Trades":[], "Win%":[],"ActiveDays":[],"Winners":[], "Losers":[], "Ri/Re":[], "Exp$":[], "AWinP":[], "ALosP":[]})

    for year in range(start_year,end_year+1,1):
        smonth=start_month if year <= start_year else 1
        emonth=12 if year != end_year else end_month
        for month in range(smonth, emonth+1,1):
            month_number+=1
            num_days = calendar.monthrange(year, month)[1]
            days = [datetime.date(year, month, day) for day in range(1, num_days+1)]
            tdict["Month"].append(month_number)
            month_name=calendar.month_name[month]+" "+str(year)
            tdict["MonthName"].append(month_name)
            net=0
            trades=0
            winners=0
            losers=0
            lpoints=0
            wpoints=0
            points=0
            count=0
            for dt in days:
                if dt in dts:
                    count+=1
                    row=ddf[ddf['Date']==dt]
                    net+=float(row.iloc[0]['Net'])
                    trades+=int(row.iloc[0]['Trades'])
                    winners+=int(row.iloc[0]['Winners'])
                    losers+=int(row.iloc[0]['Losers'])
                    #wpoints+=row.iloc[0]['WPoints']
                    #lpoints+=row.iloc[0]['LPoints']
                    #points+=row.iloc[0]['Points']

            #arisk=lpoints/losers if losers > 0 else 0
            #areward=wpoints/winners
            tdict['Net'].append(net)
            tdict['Trades'].append(trades)
            tdict['Winners'].append(winners)
            tdict['Losers'].append(losers)
            tdict["ActiveDays"].append(count)
            if trades > 0 :
                tdict['Win%'].append(round((winners/trades)*100,2))
            else:
                tdict['Win%'].append(0)
            if count > 0:
                tdict['AvgNet'].append(round((net/count),2))
            else:
                tdict['AvgNet'].append(0)
            #tdict['Ri/Re'].append(round(arisk/areward,2))
            #tdict["Exp$"].append(round(points/trades,2)*point_value)
            #tdict["AWinP"].append(round(wpoints/winners,2))
            #tdict["ALosP"].append(round(lpoints/losers,2))
    rdf=pd.DataFrame(tdict)
    return rdf


def get_progress_lines(df,frdf, ib):
    lines_list=[]
    line_color_dict={}
    CurrentTarget=ib
    running_balance=ib
    number_of_days=df.shape[0]
    tbal=frdf.iloc[0]["Net"]
    ptfactor=int(((ib + tbal) // ib))
    dict1=dict({"Day":[],"Initial":[], "Balance":[]})
    
    for i in range(1, ptfactor+1):
        num=100*i
        str1=str(num)+"%"
        lines_list.append(str1)
        line_color_dict[str1]="cyan"
        dict1[str1]=[]
    for i in range(number_of_days+2):
        for j in range(1, ptfactor+1):
            num=100*j
            str1=str(num)+"%"
            dict1[str1].append((j+1)*ib)
    
        dict1["Day"].append(i)
        dict1["Initial"].append(float(ib))
        if i==0:
            dict1["Balance"].append(ib)
        elif i >0 and i<=number_of_days:
            running_balance+=float(df.iloc[i-1]["Net"])
            dict1["Balance"].append(running_balance)
        else:
            dict1["Balance"].append(running_balance)
    df1=pd.DataFrame(dict1)
    return(df1, lines_list, line_color_dict)    



def cuDB(ufiles, op):
    processed_dfs=list()
    for uploaded_file in ufiles:
        raw_csv_pd=pd.read_csv(uploaded_file)
        csv_pd_1=raw_csv_pd[columns_tst]
        csv_pd_2=process_df(csv_pd_1)
        processed_dfs.append(csv_pd_2)
    full_df=pd.concat(processed_dfs)
    full_df.reset_index(drop=True, inplace=True)
    if op == "create":   
        full_df.to_pickle(dbLocation+st.session_state.selectedJDB)
    elif op == "update":
        file=dbLocation+st.session_state.selectedJDB
        current_df=pd.read_pickle(file)
        os.remove(file)
        final_df=pd.concat([current_df,full_df])
        final_df.reset_index(drop=True, inplace=True)
        final_df.to_pickle(file)

@st.cache
def get_tradovate_futures_margins():
    futures_margins_url="https://www.tradovate.com/resources/markets/margin/?utm_campaign=pricing&utm_source=paidsearch&utm_medium=adwords&utm_content=textad&ads_cmpid=829315388&ads_adid=124817818990&ads_matchtype=e&ads_network=g&ads_creative=514632727397&utm_term=tradovate%20margin%20requirements&ads_targetid=kwd-1455151606552&utm_source=adwords&utm_medium=ppc&ttv=2&gclid=CjwKCAjw4qCKBhAVEiwAkTYsPM_5Qlb60sydGoWUHmyZtA-gWFotbYILJMLPXmorfA5qbcqO7CYYdxoCETwQAvD_BwE"
    options=Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options, executable_path=DRIVER_PATH)
    driver.get(futures_margins_url)
    html=driver.page_source
    soup = BeautifulSoup(html,"lxml")
    table_data=soup.findAll("table")[0]
    headers = []
    for i in table_data.find_all('th'):
        title = i.text.strip()
        headers.append(title)
    df = pd.DataFrame(columns = headers)
    for j in table_data.find_all('tr'):
        row_data = j.find_all('td')
        #for tr in row_data:
        #    print(tr.text)
        row = [tr.text.strip() for tr in row_data]
        if len(row) > 0:
            length = len(df)
            df.loc[length] = row
    df=df[df["Group"] == "E-Mini Indices"]
    driver.close()
    driver.quit()
    return(df)

@st.cache
def get_earnings_yahoo(day):
    base_url="https://finance.yahoo.com/calendar/earnings?day="
    url=base_url+day
    #print(url)
    options=Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options, executable_path=DRIVER_PATH)
    driver.get(url)
    html=driver.page_source
    soup = BeautifulSoup(html,"lxml")
    table_data=soup.findAll("table")[0]
    
    headers = []
    for i in table_data.find_all('th'):
        title = i.text.strip()
        headers.append(title)
    df = pd.DataFrame(columns = headers)
    for j in table_data.find_all('tr'):
        row_data = j.find_all('td')
        row = [tr.text.strip() for tr in row_data]
        if len(row) > 0:
            length = len(df)
            df.loc[length] = row
    driver.close()
    driver.quit()
    return df

@st.cache
def get_index_components():
    ic=dict()
    nurl="https://www.slickcharts.com/nasdaq100"
    surl="https://www.slickcharts.com/sp500"
    durl="https://www.slickcharts.com/dowjones"
    
    
    #page = requests.get(nurl)
    #soup = BeautifulSoup(page.text, 'html.parser')
    #dfs=pd.read_html(page.text)
    #table = soup.find_all('table')
    options=Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options, executable_path=DRIVER_PATH)
    
    for url in [nurl, surl, durl]:
        driver.get(url)
        html=driver.page_source
        dfs=pd.read_html(html)
        if url == nurl:
            ic["nasdaq"]=dfs[0][["Company", "Symbol","Weight"]]
        elif url == surl:
            ic["sp500"]=dfs[0][["Company", "Symbol","Weight"]]
        elif url == durl:
            ic["dow"]=dfs[0][["Company", "Symbol","Weight"]]
    driver.close()
    driver.quit()
    filename=dbLocation+icpf
    if os.path.exists(filename):
        os.remove(filename)
    with open(filename, 'wb') as f:
        pickle.dump(ic,f)

def getSPDRETFs():
    xletfinfo=dict()
    murl="https://www.sectorspdr.com/sectorspdr/"
    str="IDCO.Client.Spdrs.Portfolio/Export/ExportCsv?symbol="
    f=open(dataLocation+xletfs)
    xetfs=json.load(f)
    f.close()
    for item in xetfs['XLETFs']:
        for key in item.keys():
            #print(key)
            #print(item[key])
            url=murl+str+key.lower()
            #print(url)      
            r = requests.get(url)
            filename=key.lower()+".csv"
            with open(filename, 'wb') as f:
                f.write(r.content)
            with open(filename) as f:
                lines = f.readlines()
            with open(filename, 'w') as f:
                f.writelines(lines[1:-2])
            df=pd.read_csv(filename, usecols=["Symbol", "Company Name", "Weight"])
            os.remove(filename)
            xletfinfo[key]=df
    filename=dbLocation+xletfpf
    if os.path.exists(filename):
        os.remove(filename)
    with open(filename, 'wb') as f:
        pickle.dump(xletfinfo,f)

def getStocksWithWeeklyOptions():
    weeklies=dict()
    csvf=dataLocation+weeklyOptions
    #df=pd.read_csv(csvf)
    #print(df)
    
    with open(csvf) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count=0
        change_flag=0
        for row in csv_reader:
            if line_count == 0:
                line_count += 1
                continue
            elif row[0] == "":
                continue
            elif row[0]=="Available Weeklys - Equity":
                change_flag=1
                continue
            else:
                if change_flag==0:
                    weeklies[row[0]]=("ETF", row[1])
                elif change_flag==1:
                    weeklies[row[0]]=("Stock", row[1])
                line_count += 1
    filename=dbLocation+wpf
    if os.path.exists(filename):
        os.remove(filename)
    with open(filename, 'wb') as f:
        pickle.dump(weeklies,f)

def main():
    #session state initialization
   

    #Parse Targets File
    global datadict
    (targetkeys,datadict)=processTargetsFile()
    #if st.session_state.selectedTarget ==  None:
    #    st.session_state.selectedTarget=targetkeys[-1]
    #st.session_state.selectedJDB=targetkeys[-1]+".pickle"

    #streamlit code
    cnow=datetime.datetime.now()   
    st.session_state.cyear=cnow.year
    st.session_state.cmonth=cnow.month
    st.session_state.cday=cnow.day
    
    
    yoptions=range(2020, 2025)
    moptions = list(range(1,len(calendar.month_name)))
    st.set_page_config(layout="wide")
    with st.sidebar:
        st.header("Control Panel")
        mode=st.selectbox('Operation Mode',["Setup","Dashboard", "Dataframes","Daily","Calendar", "Charting","Schedule"])
        if mode == "Calendar":
            sbcol11, sbcol22 = st.columns(2) 
            sel_year= sbcol11.selectbox('Year',yoptions,index=yoptions.index(st.session_state.cyear))
            sel_month= sbcol22.selectbox("Month", moptions, format_func=lambda x: calendar.month_name[x],index=moptions.index(st.session_state.cmonth))   
        elif mode == "Dashboard":
            st.subheader("Earnings Dates Range")
            sbcol11, sbcol22 = st.columns(2) 
            day_from=sbcol11.date_input("From",datetime.date(int(st.session_state.cyear),int(st.session_state.cmonth),st.session_state.cday))
            day_to=sbcol22.date_input("To",datetime.date(int(st.session_state.cyear),int(st.session_state.cmonth),st.session_state.cday))    
        
    if mode == "Setup":
        st.session_state.selectedMonth=st.session_state.cmonth
        st.session_state.selectedYear=st.session_state.cyear
        st.session_state.press=False
        st.header("Configuration")
        targetkeys.insert(0,"None")
        st.session_state.selectedTarget=st.radio(f"Working with Journaling Target:", targetkeys)
        st.header("DataBase Operations")
        dblist=list()
        for tgt in targetkeys:
            if tgt =="None":
                dblist.append(tgt)
            else:
                tgt1=tgt+".pickle"
                dblist.append(tgt1)
        st.session_state.selectedJDB=st.radio(f"Working with Journaling DB:", dblist)
        op1=st.radio(f"Working with DB {st.session_state.selectedJDB}", ("Display","Create","Update"))
        if op1 == "Create":
            file=dbLocation+st.session_state.selectedJDB
            if os.path.exists(file):
                os.remove(file)
            uploaded_files = st.file_uploader("Choose a CSV file", accept_multiple_files=True)
            if uploaded_files:
                cuDB(uploaded_files, "create")
        elif op1 == "Update":
            file=dbLocation+st.session_state.selectedJDB
            if os.path.exists(file):
                uploaded_files = st.file_uploader("Choose a CSV file", accept_multiple_files=True)
                if uploaded_files:
                    cuDB(uploaded_files, "update")
        elif op1 == "Display":
            file=dbLocation+st.session_state.selectedJDB
            if os.path.exists(file):
                full_df=pd.read_pickle(file)
                st.dataframe(full_df)
            else:
                st.write(f"The file: {file} does not exist")
        st.header("Data Collection")
        doptions = st.multiselect(
                                    'Ticker Classification',
                                ['Index Tickers', 'Weekly Option Tickers', 'SPDR ETF Tickers'])
        for t in doptions:
            if t == "Index Tickers":
                get_index_components()
            elif t == "Weekly Option Tickers":
                getStocksWithWeeklyOptions()
            elif t == "SPDR ETF Tickers":
                getSPDRETFs()
    elif mode == "Dataframes":
        st.subheader("Monthly Dataframe")
        st.dataframe(get_monthly_result_df(st.session_state.daily_df).style.apply(custom_style_result_week,axis=1))
        st.subheader("Weekly Dataframe")
        st.dataframe(get_weekly_result_df(st.session_state.daily_df).style.apply(custom_style_result_week,axis=1))
    elif mode == "Schedule":
        st.dataframe(createSchedule(datadict[st.session_state.selectedTarget],st.session_state.daily_df).style.apply(custom_style_schedule,axis=1))
    elif mode == "Dashboard":
        filename=dbLocation+icpf
        with open(filename, 'rb') as f:
            ic=pickle.load(f)
        symset1=set(ic["dow"]['Symbol'].tolist())
        symset2=set(ic["nasdaq"]['Symbol'].tolist())
        symset3=set(ic["sp500"]['Symbol'].tolist())
        symset=symset1.union(symset2, symset3)

        

        st.subheader("Tradovate Futures Margins")
        st.dataframe(get_tradovate_futures_margins())
        st.subheader("Earnings")
        if day_from == day_to:
            day_from_1=datetime.date.strftime(day_from,"%Y-%m-%d")
            st.subheader(day_from_1)
            df=get_earnings_yahoo(day_from_1)
            st.dataframe(df[df['Symbol'].isin(symset)])
        else:
            l1=[day_from+datetime.timedelta(days=x) for x in range((day_to-day_from).days + 1)]
            for day in l1:
                day_from_1=datetime.date.strftime(day,"%Y-%m-%d")
                st.subheader(day_from_1)
                df=get_earnings_yahoo(day_from_1)
                st.dataframe(df[df['Symbol'].isin(symset)])  
    elif mode == "Daily":
        file=dbLocation+st.session_state.selectedJDB
        print(file)
        if os.path.exists(file):
            full_df=pd.read_pickle(file)
        pt=ProcessTrades(full_df)
        pt.process_full_df(datadict[st.session_state.selectedTarget])
        st.subheader("Daily Dataframe")
        st.dataframe(pt.daily_df.style.apply(custom_style_result,axis=1))
        st.session_state.daily_df=pt.daily_df
        st.subheader("Summary Dataframe")
        pt.create_summary_df(datadict[st.session_state.selectedTarget])
        st.dataframe(pt.summary_df)
        st.dataframe(pt.summary_df_2)
        st.dataframe(pt.summary_df_3)
        dfpg, lines_list, line_color_dict=get_progress_lines(pt.daily_df, pt.summary_df, datadict[st.session_state.selectedTarget].ib)
        #Plots
        st.subheader("Daily Plots")

        df1=pt.daily_df[["Date","Trades","Winners","Losers","Long","Short"]]
        fig_stacked_bar(df1,["Winners", "Losers"],"Trades-Wnners/Losers",["green","red"])
        fig_stacked_bar(df1,["Long", "Short"],"Trades-Long/Short",["blue","cyan"])
        df2=pt.daily_df[["Date","Net"]]
        df2['Net']=df2['Net'].astype(float)
        df2['CumNet']=df2['Net'].cumsum()
        df2['PnL']=df2['CumNet']+datadict[st.session_state.selectedTarget].ib
        #st.dataframe(df2)
        fig_line(df2,["PnL"],"PnL")
        ylist=lines_list+["Initial",  "Balance"]
        line_color_dict.update({
                              "Initial":"black",
                              "Balance":"green"
                          })
        fig = px.line(dfpg, x='Day', y=ylist, markers=True,
                          color_discrete_map=line_color_dict
                          )
        st.write(fig)

        df2['Color']=np.where(df2['Net']<0, "red", "green")
        fig_combo(df2)
        df2["ActiveDays"]=range(1,len(df2)+1)
        df2["AvgDailyReturn"]=df2['CumNet']/df2['ActiveDays']
        fig_line(df2,["AvgDailyReturn"],"AvgDailyReturn")





    elif mode == "Calendar":
        st.subheader("Calendar")
        sbcol1, sbcol2 = st.columns(2)
        

        sbcol1.button("Prev", on_click=prev_month, args=(st.session_state.selectedMonth,st.session_state.selectedYear, yoptions))
        sbcol2.button("Next", on_click=next_month, args=(st.session_state.selectedMonth,st.session_state.selectedYear, yoptions))
        
    
        if st.session_state.press:
            sel_month=st.session_state.selectedMonth
            sel_year=st.session_state.selectedYear
        if sel_month != st.session_state.selectedMonth or sel_year != st.session_state.selectedYear:
            cal_month(sel_month, sel_year, st.session_state.daily_df)  
            st.session_state.selectedMonth=sel_month
            st.session_state.selectedYear=sel_year  
        else:
            cal_month(st.session_state.selectedMonth,st.session_state.selectedYear, st.session_state.daily_df)

if __name__ == "__main__" or __name__ == "__tr_app__":
    # execute only if run as a script
    main()