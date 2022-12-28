# -*- coding: utf-8 -*-
"""
任务4：可视化
"""
#%% 1. 导入模块、包、类
from ibapi.client import EClient, HistoricalTick
from ibapi.order import Order
from ibapi.wrapper import EWrapper, CommissionReport, Contract
from ibapi.utils import iswrapper
from ibapi.execution import Execution, ExecutionFilter
from ibapi.account_summary_tags import AccountSummaryTags

import collections
from threading import Thread
import time
from datetime import datetime
import pandas as pd
import talib as ta
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
plt.rcParams['font.sans-serif'] = ['Kaiti']
plt.rcParams['axes.unicode_minus'] = False


#%% 2. 定义合约
def FX_Contract(symbol: str)-> Contract:
    contract = Contract()
    contract.symbol = symbol
    contract.secType = 'CASH'
    contract.currency = "USD"
    contract.exchange = 'IDEALPRO'
    return contract

#%% 3. 自定义交易函数
def req_current_time() -> str:
    current_IDE_time = datetime.now().strftime('%H:%M:%S')  # 任务2：每秒打印时间显示
    #current_IDE_time = datetime.now().strftime('%H:%M')  # 任务2：每秒打印时间显示
    return current_IDE_time


def req_current_TWS_time() -> str:
    current_TWS_time = ibapi.current_TWS_time.strftime('%H:%M')
    return current_TWS_time


def log_to_localfile(content:str):
    """作用：日志记录"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    content = current_time +':'+ content
    space = '\n'
    a = open(file = 'TWS_log.txt', mode = 'a+')
    a.write(space + content + space)
    a.close()
    
def donchian_high(df:pd.DataFrame, n:int, name:str) -> None:
    """
    作用：计算唐奇安通道的上轨
    参数：
        df 数据
        n 表示周期
        name 表示在 df 中新的列名，用来存储唐奇安通道的上轨数值
    """
    length = len(df)
    if length < n:
        print('获取数据太短，不能计算唐奇安通道')
        return 
    df['{}'.format(name)] =  np.NAN  # 初始化空数据框
    for i in range(n, length):
        df['{}'.format(name)] [i] = df['High'][i-n:i].max()


def donchian_low(df:pd.DataFrame, n:int, name:str) -> None:
    """
    作用：计算唐奇安通道的上轨
    参数：
        df 数据
        n 表示周期
        name 表示在 df 中新的列名，用来存储唐奇安通道的下轨数值
    """
    length = len(df)
    if length < n:
        print('获取数据太短，不能计算唐奇安通道')
        return 
    df['{}'.format(name)] =  np.NAN  # 初始化空数据框
    for i in range(n, length):
        df['{}'.format(name)] [i] = df['Low'][i-n:i].max()
        
        
#%% 4. IBapi 类定义
class IBapi(EClient, EWrapper):
    """
    需要这么几方面数据：
    # 1. 行情数据：
    当前合约的所有时间框架下的数据，需要能够得到在当前时刻的，过去n根bar数据OHLCV
    需要获取实时数据，实时tick数据，包含成交数据，以及报价数据

    2. 账户数据
    当前账户信息
    需要得到当前仓位信息，仓位放入dataframe中
    历史成交

    3. 订单管理数据
    订单发送
    当前挂单状态
    历史订单
    """
    def __init__(self, addr, port, client_id):
        posns = collections.defaultdict(list)  # 这是什么意思？

        EClient.__init__(self, self)
        self.data = []  # self.data:list 必须放置在这个位置，因为是以流形式存在
        self.historical_data_end = False  # ?
        self.current_position = [] # 自定义的属性，用于保存当前
        self.connect(addr, port, client_id)
        self.current_TWS_time = datetime.now()

        # 客户端线程
        thread = Thread(target=self.run)
        thread.start()

    @iswrapper
    def currentTime(self, cur_time):  # 返回当前时间戳：任务2√
        t = datetime.fromtimestamp(cur_time)
        print('Current time:{}'.format(t))
        self.current_TWS_time = t
    
    @iswrapper    
    def historicalData(self, reqId: int, bar):  # 获得行情数据：任务3√
        # 这里原来为何没有函数注解呢？这里不能用 bar: Bar，会报错：name 'Bar' is not defined
        # print(f'Time: {bar.date} Open:{bar.open} High: {bar.high} Low: {bar.low} Close: {bar.close}')
        self.data.append([bar.date, bar.open, bar.high, bar.low, bar.close])
            # 此函数重构了historicalData函数，响应reqhistoricalData的请求，返回reqId:int，和bar:Bar
        # Bar中包含OHLC和Volume，Volume在外汇中不好使，reqhistoricalData中使用"TRADES",这是个错误
        # 如果是股票则需要成交量，外汇暂可以认为成交量oo
        # https://interactivebrokers.github.io/tws-api/historical_bars.html  
        
    @iswrapper  
    def historicalDataEnd(self, reqId:int, start: str, end:str):   # 标记历史数据结束：任务3√
        # Marks the ending of the historical bars reception. 
        # once all candlesticks have been received the IBApi.EWrapper.historicalDataEnd marker will be sent. 
        
        self.historical_data_end = True  # 这是什么意思啊
        print('HistoricalDataEnd.ReqId:', reqId, 'from', start, 'to', end)
    
    def storehistoricalData(self):  # 任务3 √
        # 完全自定义函数，将历史数据存入 df 中
        df = pd.DataFrame(self.data, columns = ['DateTime', 'Open', 'High', 'Low', 'Close'])
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        df.set_index(['DateTime'], inplace = True)
#         df.to_csv('eurusd.csv') 
        return df
        # print(df)
    
        
#%% 5. 任务实现：隔一段时间获得当前的行情数据并保存下来

# 定义唐奇安通道相关参数
n1 = 20
n3 = 10

# 是否进行 K线图可视化
open_graph = True

# 创建交易合约类
eurusd_contract = FX_Contract('EUR')

# 定义每次成交量 1 手
trading_volume_per_lot = 100000  # 标准手是：10W， 迷你手是 1W
number_of_lots = 1  # 手数
quantity = trading_volume_per_lot * number_of_lots

log_to_localfile('程序开始运行')  # 记录日志

# TWS 连接
clientId = np.random.randint(1,100) 
ibapi = IBapi('127.0.0.1', 7497, clientId)
time.sleep(0.5)

if ibapi.isConnected()==False:  
        # 此处需要注意有错误不能退出，不能让程序和市场处在断连的状态
        print (req_current_TWS_time()+"当前无TWS连接！尝试重新连接！")
        
        # 为了避免clientId被占用，启用随机数作为连接clientId
        clientId = np.random.randint(1,100) 
        ibapi = IBapi('127.0.0.1', 7497, clientId)
        time.sleep(1)
else:
    # 当前TWS时间 
    current_TWS_time=req_current_TWS_time()
    current_IDE_time=req_current_time()
    print('Current time is:', current_IDE_time)

    # 请求历史数据。一般情况下需要更长时间返回，给定3秒钟；其他请求可以酌情减少
    ibapi.reqHistoricalData(reqId=110, contract = eurusd_contract, endDateTime='', durationStr='3 D', \
                                barSizeSetting='1 hour', whatToShow='bid', useRTH = 1, formatDate=1, \
                                    keepUpToDate=False, chartOptions=[])
    time.sleep(3)
    print('Historical data is retrieved.')

    # 调用自定义函数存储历史数据
    df = ibapi.storehistoricalData()
#         df.to_csv('eurusd.csv') 

    # 计算唐奇安通道: df 数据；n 表示周期；name 表示在 df 中新的列名，用来存储唐奇安通道的上轨数值
    donchian_high(df,n1, 'donchian_up' )  
    donchian_low(df,n1, 'donchian_down' )  

    donchian_high(df, n3, 'donchian_up_n3')
    donchian_low(df,n3, 'donchian_down_n3' )  

    # 将原始数据以及计算好的唐奇安通道保存至文件
    df.to_excel("eurusd.xlsx")
    print ("数据获取完成！")

    # 行情及唐奇安通道可视化，亦可用于进出场位置标记
    if open_graph == True:  # 显示 n1, n2, n3 唐奇安通道
        add_plot = [
            mpf.make_addplot(df['donchian_up'], markersize = 8, color = 'g'),
            mpf.make_addplot(df['donchian_down'], markersize = 8, color = 'r'),
#                 mpf.make_addplot(df['donchian_up_n2'], markersize = 8, color = 'b'),
#                 mpf.make_addplot(df['donchian_up_n2'], markersize = 8, color = 'y'),
            mpf.make_addplot(df['donchian_up_n3'], markersize = 8, color = 'c'),
            mpf.make_addplot(df['donchian_down_n3'], markersize = 8, color = 'm'),
        ]
        title = 'EURUSD'
        style = mpf.make_mpf_style(base_mpf_style = 'yahoo', rc={'font.family': 'SimHei'})
       # try:
            # 画图。包含K线图，唐奇安通道，进出位置
        graph = mpf.plot(df, addplot = add_plot, title = title, ylabel = 'Price',\
                         type = 'candle', style = style, show_nontrading = False)
        #except:
         #   print('画图失败')

    time.sleep(57)  