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



######Globals########


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

    @property
    def exset(self):
        return self._exset


class ProcessTrades:

    def __init__(self, df):
        self._full_df=df
        self._days_dict=dict()
        self._daily_df=pd.DataFrame()
        self._summary_df=pd.DataFrame()

    @property
    def summary_df(self):
        return self._summary_df
        
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
        tdict["Win20s"]=[w20s]
        if winners > 0:
            tdict["Win20s%"]=[('%f' % round((w20s/winners)*100,2)).rstrip('0').rstrip('.')]
        self._summary_df=pd.DataFrame(tdict)

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
        #tdict["Long"]=[longs]
        #tdict["LongW"]=[long_winners]
        #tdict["Short"]=[shorts]
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
        full_df.to_pickle(dbLocation+PersonalTransactionDB)
    elif op == "update":
        file=dbLocation+PersonalTransactionDB
        current_df=pd.read_pickle(file)
        os.remove(file)
        final_df=pd.concat([current_df,full_df])
        final_df.reset_index(drop=True, inplace=True)
        final_df.to_pickle(file)

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
            file=dbLocation+PersonalTransactionDB
            if os.path.exists(file):
                os.remove(file)
            uploaded_files = st.file_uploader("Choose a CSV file", accept_multiple_files=True)
            if uploaded_files:
                cuDB(uploaded_files, "create")
        elif op1 == "Update":
            file=dbLocation+PersonalTransactionDB
            if os.path.exists(file):
                uploaded_files = st.file_uploader("Choose a CSV file", accept_multiple_files=True)
                if uploaded_files:
                    cuDB(uploaded_files, "update")
        elif op1 == "Display":
            file=dbLocation+PersonalTransactionDB
            if os.path.exists(file):
                full_df=pd.read_pickle(file)
                st.dataframe(full_df)
            else:
                st.write(f"The file: {file} does not exist")
    elif mode == "Schedule":
        st.dataframe(createSchedule(datadict[st.session_state.selectedTarget]))
    elif mode == "Daily":
        file=dbLocation+PersonalTransactionDB
        if os.path.exists(file):
            full_df=pd.read_pickle(file)
        pt=ProcessTrades(full_df)
        pt.process_full_df(datadict[st.session_state.selectedTarget])
        st.subheader("Daily Dataframe")
        st.dataframe(pt.daily_df)
        st.subheader("Summary Dataframe")
        pt.create_summary_df(datadict[st.session_state.selectedTarget])
        st.dataframe(pt.summary_df)


if __name__ == "__main__" or __name__ == "__tr_app__":
    # execute only if run as a script
    main()