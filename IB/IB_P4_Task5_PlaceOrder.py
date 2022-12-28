# -*- coding: utf-8 -*-
"""
任务5：下单
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
    
    @iswrapper
    def position(self, account: str, contract: Contract, position: float,avgCost: float):  # 返回当前仓位信息：任务5√

        """
        参考链接：https://interactivebrokers.github.io/tws-api/interfaceIBApi_1_1EWrapper.html#af4105e2dae9efd6f6bb56f706374c9d6
        """
        super().position(account, contract, position, avgCost)
        # print("Position.", "Account:", account, "Symbol:", contract.symbol,\
              # "SecType:", contract.secType, "Currency:", contract.currency,"Position:", position, "Avg cost:", avgCost)
        self.current_position.append([account,contract.symbol,contract.secType,contract.currency,position,avgCost])
        # 保存账号，合约代码，合约类型，合约货币，合约头寸，平均价格
        # current_position 是 IBapi 类自己的一个属性, 列表类型
   
    def get_current_position_in_df(self):  # 自定义函数: 任务5√
        if self.isConnected():
            self.position_df = pd.DataFrame(self.current_position, \
                                            columns=['Account', 'Symbol','SecurityType','Currency', 'Position', 'AverageCost'])
            return self.position_df
        else:
            return 0    
    
    def Find_Position(self, Account: str, Symbol:str, secType:str, Currency):  # 自定义函数：任务5√
        position = self.position_df[(self.position_df['Account']==Account) &
                                     (self.position_df['Symbol']==Symbol) & 
                                     (self.position_df['SecurityType']==secType) &
                                     (self.position_df['Currency']==Currency)]
        position=position.reset_index(drop=True)
        print(position)
        return position['Position'][0]
        
    
    @iswrapper
    def nextValidId(self, orderId: int):  # 获得下一个可用订单编号：任务5√
        super().nextValidId(orderId)
        self.nextorderId = orderId
        # print('The next valid order id is: ', self.nextorderId)
    
    @iswrapper
    def openOrder(self, orderId, contract, order,orderState):  # placeorder 的响应函数 任务5√
        super().openOrder(orderId, contract, order, orderState)
        print("OpenOrder. PermId: ", order.permId, "ClientId:", order.clientId, " OrderId:", orderId, \
              "Account:", order.account, "Symbol:", contract.symbol, "SecType:", contract.secType,
              "Exchange:", contract.exchange, "Action:", order.action, "OrderType:", order.orderType,
              "TotalQty:", order.totalQuantity, "CashQty:", order.cashQty, 
                "LmtPrice:", order.lmtPrice, "AuxPrice:", order.auxPrice, "Status:", orderState.status)
    
          # order.contract = contract
          # self.permId2ord[order.permId] = order
    
    @iswrapper
    def orderStatus(self, orderId, status: str, filled: float,remaining: float, avgFillPrice: float,\
                    permId: int,parentId: int, lastFillPrice: float, clientId: int,whyHeld: str, mktCapPrice: float):
        # placeorder 的响应函数 任务5√
        super().orderStatus(orderId, status, filled, remaining,avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
        print("OrderStatus. Id:", orderId, "Status:", status, "Filled:", filled,"Remaining:", remaining, "AvgFillPrice:", avgFillPrice,
               "PermId:", permId, "ParentId:", parentId, "LastFillPrice:",lastFillPrice, "ClientId:", clientId, "WhyHeld:",whyHeld, "MktCapPrice:", mktCapPrice)
    
      
#%% 5. 任务实现：隔一段时间获得当前的行情数据并保存下来
time_list = ["00:01","01:01","02:01","03:01","04:01","05:01",\
            "06:01","07:01","08:01","09:01","10:01","11:01",\
                "12:01","13:01","14:22","15:01","16:01","17:16"\
                    "18:01","19:01","20:01","21:01","22:01","23:01"]

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

while True:
    if ibapi.isConnected() == False:  # EClient 的函数 true if connection has been established, false if it has not. 
        # https://interactivebrokers.github.io/tws-api/classIBApi_1_1EClient.html#ab8e2702adca8f47228f9754f4963455d
        # 此处需要注意有错误不能退出，不能让程序和市场处在断连的状态   
        print(req_current_TWS_time()+'当前无 TWS 连接！尝试重新连接！')

        # 为了避免clientId被占用，启用随机数作为连接clientId
        clientId = np.random.randint(1, 100)
        ibapi = IBapi('127.0.0.1', 7497, clientId)
        time.sleep(0.5)
        continue  # 这里为什么要加 continue 呢？又没有循环
    else:
        print ("TWS 已经连接!")
        
        # 获得当前仓位情况
        ibapi.reqPositions()  # 这句代码还要单独执行么？后面调用 get_current 不会类内部自动运行么
        time.sleep(1)
        current_position = ibapi.get_current_position_in_df() # 这句代码还要单独执行么？后面调用 Find_Position 不会类内部自动运行么
        position = ibapi.Find_Position('DU4257965', 'EUR', 'CASH', 'USD' )
        
        # 当前TWS时间 
        current_TWS_time = req_current_TWS_time()
        current_IDE_time = req_current_time()
        print('Current time is:', current_IDE_time)

        # 请求历史数据。一般情况下需要更长时间返回，给定3秒钟；其他请求可以酌情减少
        
        if current_IDE_time in time_list:
            print('**当前时间：', current_IDE_time,'**')
            ibapi.reqHistoricalData(reqId=110, contract = eurusd_contract, endDateTime='', durationStr='3 D', \
                                        barSizeSetting='1 hour', whatToShow='bid', useRTH = 1, formatDate=1, \
                                            keepUpToDate=False, chartOptions=[])
            time.sleep(3)
            
            # 调用自定义函数存储历史数据
            df = ibapi.storehistoricalData()

            # 计算唐奇安通道: df 数据；n 表示周期；name 表示在 df 中新的列名，用来存储唐奇安通道的上轨数值
            donchian_high(df,n1, 'donchian_up' )  
            donchian_low(df,n1, 'donchian_down' )  
            donchian_high(df, n3, 'donchian_up_n3')
            donchian_low(df,n3, 'donchian_down_n3' )  

            # 将原始数据以及计算好的唐奇安通道保存至文件
            df.to_excel("EURUSD.xlsx")
            print ("数据获取完成！")
            
        # 仓位判断
        if position == 0:  # 无仓位时，满足条件则开仓
            
            if buy_condition():
                Place_Market_Order(eurusd_contract, 'buy', quantity)
                # 开仓之后避免同一分钟之内连续开仓，可加以控制
                # 只需要挺过100秒，则不再继续开仓
                # 此位置更加严格的写法是返回开仓成功以后再沉睡100秒，如不成功则需要人工干预
                # print (datetime.now().strftime("%H:%M")+"开多仓")
                log_to_localfile(req_current_time()+"开多仓")
                time.sleep(1)
            
            if sell_condition():
                Place_Market_Order(eurusd_contract, 'sell', quantity)
                # print (datetime.now().strftime("%H:%M")+"开空仓")
                log_to_localfile(req_current_time()+"开空仓")
                time.sleep(1)
                
        elif position > 0:  # 有做多仓位时，满足条件则平仓
            if close_buy_condition():
                Place_Market_Order(eurusd_contract, 'sell', quantity)
                log_to_localfile(req_current_time()+"多仓平仓")
                time.sleep(1)
            
        elif position < 0:  # 有做空仓位时，满足条件则平仓
            if close_buy_condition():
                    Place_Market_Order(eurusd_contract, 'buy', quantity)
                    # print (datetime.now().strftime("%H:%M")+"空仓平仓")
                    log_to_localfile(req_current_time()+"空仓平仓")
                    time.sleep(1)
                    
        time.sleep(60)  # 1 min 只需要下一次单，每一小时
        
    time.sleep(10)