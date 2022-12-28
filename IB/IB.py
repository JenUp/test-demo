# EClient和EWrapper在不同的库中导入，它们分别做为IDE（Python编程端口）与TWS的交互的必要包使用
#%% 导入必要库
# 打开连接，接收请求 
from ibapi.wrapper import EWrapper 

# 引用合约类 Contract，Contract类用于创建合约使用
# 打开连接，发送请求和接收请求 EClinet
from ibapi.client import EClient, Contract  

# order类用于创建订单使用
from ibapi.order import Order  

# iswrapper 用来重构 EWrapper 下的所有函数的
from ibapi.utils import iswrapper  

# threading用于开启多线程功能
from threading import Thread  

# 导入时间库，用于后续停时使用， 延迟控制
import time  

# 导入日期时间库，用于后续本机时间的获取、修改时间格式
from datetime import datetime  

# 导入pandas库，用于后续存储历史数据
import pandas as pd  
import numpy as np

import sys
from IPython.display import clear_output as clear  # 清除 Jupyter Notebook 的输出结果

from ibapi.client import EClient, HistoricalTick# , ClientException
from ibapi.wrapper import EWrapper, CommissionReport, Contract
from ibapi.execution import Execution, ExecutionFilter
from ibapi.account_summary_tags import AccountSummaryTags

import collections
# import talib as ta
import matplotlib.pyplot as plt
# import mplfinance as mpf
plt.rcParams['font.sans-serif'] = ['Kaiti']
plt.rcParams['axes.unicode_minus'] = False

from ibapi.client import EClient, HistoricalTick# , ClientException
from ibapi.wrapper import EWrapper, CommissionReport, Contract
from ibapi.execution import Execution, ExecutionFilter
from ibapi.account_summary_tags import AccountSummaryTags


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
当前挂单状态A
"""
#%% 定义IB类
# =============================================================================
# 用来定义IB连接、数据接收
# =============================================================================
class IBapi(EClient, EWrapper):  # 类的继承：IB核心是多继承，同时继承 EClient 和 EWrapper
    def __init__(self, addr, port, client_id):  # 每次连接，需要自动设置一些基本参数
        """
        addr: TWS 运行的本机地址
        port: 端口号 7497（模拟账号）
        client_id: TWS可以同时连接32个客户端，通过 client_id 来识别客户端
        """
        EClient. __init__(self, self)  # 因为类是双继承，所以构造函数需要给出2个参数，但因为2个都是自己，所以是2个 self
               
        self.data = []  # self.data:list 必须放置在这个位置，因为是以流形式存在
        self.historical_data_end = False  # 
        self.order_id = None  # 初始化订单编号 (order_id)
        # self.current_TWS_time = datetime.now()   # 本机时间
        # TWS    Server
        # IDE   本机时间 local
      
        # self.symbol=""        
        self.current_position = []  # 自定义属性，保存当前仓位
        self.all_positions = pd.DataFrame([], 
                                          columns = ['Account','Symbol', 'Quantity', 'Average Cost', 'Sec Type'])
    
        posns = collections.defaultdict(list)  # 这是什么意思？    
        
        self.connect(addr, port, client_id)  # 继承自 EClient, 连接至TWS
        #这个地方开启了一个新的线程，使得发送数据和接收数据不在同一通道处
        
        # Lanch the client thread 开启多线程任务
        thread = Thread(target = self.run)
        thread.start()
    
    #%% 通用功能        
    @iswrapper        
    def error(self, reqId, code, msg):
        ''' Called if an error occurs '''
        print('错误代码： {}: {}'.format(code, msg))     
        # print('Error Code:{}, ReqID:{},Error Message:{}'.format(code, reqId, msg))
        # error code, ReqID, Error Message
        
    #%% 1. 打印时间戳
    #此函数只用于打印当前计算机时间，不是IB服务器时间, 返回当前时间戳
    @iswrapper
    # https://interactivebrokers.github.io/tws-api/interfaceIBApi_1_1EWrapper.html#a7004c6c027c90ecdc1f5c68759e37fd2
    # TWS's current time. TWS is synchronized with the server (not local computer) using NTP and this function will receive the current time in TWS. 
    def currentTime(self, cur_time):  # 响应函数：将 currenTime 函数作为参数，传递给 iswrapper
        t = datetime.fromtimestamp(cur_time)
        print('本机时间: {}'.format(t))
        self.current_TWS_time = t

    #%% 2. 获取合约信息
    @iswrapper
    def symbolSamples(self, reqId, descs):
    
        # 打印所有交易工具的个数 Print the symbols in the returned results
        print('Number of descriptions: {}'.format(len(descs)))
        print ("\n****\n")
        # print(descs)
        print ("type:",type(descs))
        print ("\n****\n")
        for desc in descs:
            print('Symbol: {}'.format(desc.contract.symbol))


        # 选择第一个交易工具 Choose the first symbol
        self.symbol = descs[0].contract.symbol


    @iswrapper
    def contractDetails(self, reqId, details):
        # https://interactivebrokers.github.io/tws-api/classIBApi_1_1ContractDetails.html
        print ("\n")
        print ("====合约信息====\n")
        print('合约名称: {}'.format(details.longName))
        print('合约类别: {}'.format(details.category))
        print('合约子类别: {}'.format(details.subcategory))        
        print('合约ID: {}\n'.format(details.contract.conId))
        print(dir(details))
        # 如果想查看其他金融工具的属性，执行print (dir(details))



    @iswrapper
    def contractDetailsEnd(self, reqId):
        print('合约信息传递结束')


    #%% 3. 获取行情信息
    @iswrapper
    def tickByTickMidPoint(self, reqId, tick_time, midpoint):
        ''' Called in response to reqTickByTickData '''

#         print('tickByTickMidPoint - Midpoint tick: {}'.format(midpoint))
        print('tick报价中间值: {}'.format(midpoint))

    @iswrapper
    def tickPrice(self, reqId, field, price, attribs):
        ''' Called in response to reqMktData '''
#         print('tickPrice - field: {}, price: {}'.format(field, price))
        print('tick价格 - 字段: {}, 价格: {}'.format(field, price))
        
 # 	def tickPrice(self, reqId, tickType, price, attrib):
 # 		if tickType == 2 and reqId == 1:
 # 			print('Callback function of reqMktData,reqId is: ', reqId)
 # 			print('tickType is: ', tickType)
 # 			print('The current ask price is: ', price)
 # 			print('attrib is: ', attrib)      
 
      # ''' Called in response to reqMktData '''
      #   if field == 0:
      #       self.ask_price = price
      #       print('ask price: {}'.format(self.ask_price))
      #   elif field == 2:
      #       self.bid_price = price
      #       self.ask_price = price
      #       print('ask price: {}'.format(self.ask_price))
      #   elif field == 9:
      #       self.close_price = price
      #       self.ask_price = price
      #       print('ask price: {}'.format(self.ask_price))
      #   else:
      #       print('tickPrice - field: {}, price: {}'.format(field, price))  

    @iswrapper
    def tickSize(self, reqId, field, size):
        ''' Called in response to reqMktData '''

        print('tick交易量 - 字段: {}, 交易量: {}'.format(field, size))
# 以上两个函数都有field字段： 0-bid size, 1-bid price, 2-ask price,3-ask size
# 4-last price, 5-last size,6-highest price of the day 7-lowest price of the day
# 8-trading volume for the day, 9-closing price for the previous day
# 10-bid option computation 11-ask option computation
# 11 ask option computation, 12-last option computation, 
    @iswrapper
    def realtimeBar(self, reqId, time, open, high, low, close, volume, WAP, count):
        ''' Called in response to reqRealTimeBars '''

        print('实时蜡烛图 - 开盘价格: {}'.format(open))

    @iswrapper
    def historicalData(self, reqId, bar):  # 获得行情数据
        ''' Called in response to reqHistoricalData '''
        
        print(f'Time: {bar.date} Open:{bar.open} Close: {bar.close}')
        self.data.append([bar.date, bar.open,bar.high,bar.low,bar.close])
            # 此函数重构了historicalData函数，响应reqhistoricalData的请求，返回reqId:int，和bar:Bar
        # Bar中包含OHLC和Volume，Volume在外汇中不好使，reqhistoricalData中使用"TRADES",这是个错误
        # 如果是股票则需要成交量，外汇暂可以认为成交量oo
    
    # 这里原来为何没有函数注解呢？这里不能用 bar: Bar，会报错：name 'Bar' is not defined
    # print(f'Time: {bar.date} Open:{bar.open} High: {bar.high} Low: {bar.low} Close: {bar.close}')
        self.data.append([bar.date, bar.open, bar.high, bar.low, bar.close])
        # 此函数重构了historicalData函数，响应reqhistoricalData的请求，返回reqId:int，和bar:Bar
    # Bar中包含OHLC和Volume，Volume在外汇中不好使，reqhistoricalData中使用"TRADES",这是个错误
    # 如果是股票则需要成交量，外汇暂可以认为成交量oo
    # https://interactivebrokers.github.io/tws-api/historical_bars.html  
        

        print('历史数据 - 收盘价格: {}'.format(bar.close))
        
    @iswrapper  
    def historicalDataEnd(self, reqId:int, start: str, end:str):   # 标记历史数据结束
        # super().historicalDataEnd(reqId, start, end)
        # Marks the ending of the historical bars reception. 
        # once all candlesticks have been received the IBApi.EWrapper.historicalDataEnd marker will be sent. 
        self.historical_data_end = True  # 这是什么意思啊
        print('HistoricalDataEnd.ReqId:', reqId, 'from', start, 'to', end)    
        

    @iswrapper
    def fundamentalData(self, reqId, data):
        ''' Called in response to reqFundamentalData '''

        print('基本面数据： ' + data)
     
    
    def storeHistoricalData(self):  # ？？？
        # 完全自定义函数，将历史数据存入 df 中
        df = pd.DataFrame(self.data, columns = ['DateTime', 'Open', 'High', 'Low', 'Close'])
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        df.set_index(['DateTime'], inplace = True)
#         df.to_csv('eurusd.csv') 
        return df
        # print(df)
    
    
    
    #%% 4. 提交订单及获取
    @iswrapper
    def nextValidId(self, order_id):
        ''' Provides the next order ID  '''
        # 返回下一个可用的订单编码
        self.order_id = order_id
        print('Order ID: {}'.format(order_id))


    @iswrapper
    def openOrder(self,order_id, contract, order, state):
        """
        作用：订单传送响应（Called in response to the submitted order）
        参数：
            orderId: the order's unique id
            contract: the order's Contract.
            order: the currently active Order.
            orderState: the order's OrderState 订单状态属性包括：https://interactivebrokers.github.io/tws-api/classIBApi_1_1OrderState.html
        """
        print('Order status:  {}'.format(state.status))
        print('Commission charged: {}'.format(state.commission))
        

    @iswrapper
    def orderStatus(self,order_id, status, filled, remaining, avgFillPrice, \
        permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        ''' Check the status of the subnitted order '''
        """
        作用：查看当前订单状态
        参数：
            orderId: the order's client id.
            status: the current status of the order. 
                PendingSubmit - indicates that you have transmitted the order, but have not yet received confirmation that it has been accepted by the order destination. 
                PendingCancel - indicates that you have sent a request to cancel the order but have not yet received cancel confirmation from the order destination. At this point, your order is not confirmed canceled. It is not guaranteed that the cancellation will be successful. 
                PreSubmitted - indicates that a simulated order type has been accepted by the IB system and that this order has yet to be elected. The order is held in the IB system until the election criteria are met. At that time the order is transmitted to the order destination as specified . 
                Submitted - indicates that your order has been accepted by the system. ApiCancelled - after an order has been submitted and before it has been acknowledged, an API client client can request its cancelation, producing this state. 
                Cancelled - indicates that the balance of your order has been confirmed canceled by the IB system. This could occur unexpectedly when IB or the destination has rejected your order. 
                Filled - indicates that the order has been completely filled. Market orders executions will not always trigger a Filled status. 
                Inactive - indicates that the order was received by the system but is no longer active because it was rejected or canceled.
            filled: number of filled positions.
            remaining: the remnant positions.
            avgFillPrice: average filling price.
            permId: the order's permId used by the TWS to identify orders.
            parentId: parent's id. Used for bracket and auto trailing stop orders.
            lastFillPrice: price at which the last positions were filled.
            clientId: API client which submitted the order.
            whyHeld: this field is used to identify an order held when TWS is trying to locate shares for a short sell. The value used to indicate this is 'locate'.
            mktCapPrice: If an order has been capped, this indicates the current capped price. 
        """
        print('Number of filled positions: {}'.format(filled))
        print('Average fill price: {}'.format(avgFillPrice))

    @iswrapper
    def position(self,account, contract, pos, avgCost):
        ''' Read information about the account's open positions '''
        print('Position in {}: {}'.format(contract.symbol, pos))






    @iswrapper
    def accountSummary(self, reqId: int, account: str, tag: str, value: str,currency: str):
        """Returns the data from the TWS Account Window Summary tab in
        response to reqAccountSummary()."""        
        ''' Read information about the account '''
        print('Account {}: {} = {}'.format(account, tag, value))

    
    #%% 其他函数
    def headTimestamp(self, reqId:int, headTimestamp:str):
      print("HeadTimestamp. ReqId:", reqId, "HeadTimeStamp:", headTimestamp)
  
    
  
    def historicalTicks(self, reqId, ticks, done):
        for tick in ticks:
            print("HistoricalTick. ReqId:", reqId, tick)
    
    
    def managedAccounts(self, accountsList: str):
        super().managedAccounts(accountsList)
        print("Account list:", accountsList)    
    
    
    
#%% 定义合约（ Define Contract ）
# 函数用来定义合约, 更多合约类型可以参考 TWS API 安装路径下：C:\TWS API\samples\Python\Testbed\ContractSamples.py

# 写一个自定义函数，返回外汇合约
def FX_Contract(symbol: str):
    """
    定义查询合约属性，服务器根据属性匹配合约返回数据，如果对应到一个以上的合约会报错
    :param symbol: 底层证券代码  ，比如 ’EUR', 'APPL'
    :param secType: 证券类型，股票：‘STK', 外汇：’CASH', 商品：‘CMDTY', 指数：’IND'...
    :param currency: 货币
    :param exchange: 交易所
    :return: 返回定义好的合约
    """
    contract = Contract()  # 实例化 Contract 类
    contract.symbol = symbol  # 底层证券代码  
    contract.secType =  'CASH'  # 证券类型 Security type
    contract.currency = "USD"  # 货币
    contract.exchange = 'IDEALPRO'  # 交易所
    return contract


#自定义函数返回股票合约
def Stock_Contract(symbol: str): # 函数注解：详见《Python学习手册》 p.562 Python 3.X 中的函数注解
    contract = Contract()
    contract.symbol = symbol
    contract.secType = 'STK'
    contract.currency = "USD"
    contract.exchange = 'SMART'
    return contract


def Future_Contract(symbol: str):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = 'STK'
    contract.currency = "USD"
    contract.exchange = 'SMART'
    return contract


def Index_Contract(symbol: str):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = 'IND'
    contract.currency = "USD"
    contract.exchange = 'SMART'
    return contract

def Options_Contract(symbol: str):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = 'OPT'
    contract.currency = "USD"
    contract.exchange = 'BOX'
    return contract


#%% 自定义交易函数
def req_current_time() ->str:
    current_IDE_time = datetime.now().strftime('%H:%M:%S')  # 任务2：每秒打印时间显示
    #current_IDE_time = datetime.now().strftime('%H:%M')  # 任务2：每秒打印时间显示
    return current_IDE_time


def req_current_TWS_time(client) -> str:  # 错误，返回的是本机时间
    current_TWS_time = client.current_TWS_time.strftime('%H:%M:%S')
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


def Place_Market_Order( Contract: Contract, Action: str, Quantity: float):
   order = Order()
   order.action  = Action
   order.totalQuantity = Quantity
   order.orderType = 'mkt'
   # order.lmtPrice = 1.15
   order.transmit = True
   
   # 获得下一个可用订单编号
   client.reqIds(-1)
   time.sleep(0.5)
   
   if ibapi.nextorderId:
       ibapi.placeOrder(ibapi.nextorderId, Contract, order)
       """执行之后，响应函数为 openOrder 和 orderStatus"""
       time.sleep(2)
   else:
       print('Order ID not received. Ending application.')
       sys.exit()     
       
   
def buy_condition() -> bool:  # 做多
    if df['High'][-2] > df['donchian_up'][-2] and df['High'][-3] < df['donchian_up'][-3]:    # 比较运算符的优先级 > 逻辑与
        return True
    else:
        return False
    
    
def sell_condition() -> bool:  # 做空
    if df['Low'][-2] < df['donchian_down'][-2] and df['Low'][-3] > df['donchian_down'][-3]:    # 比较运算符的优先级 > 逻辑与
        return True
    else:
        return False
    

def close_buy_condition() -> bool:  # 多头平仓
    if df['Low'][-2] < df['donchian_down_n3'][-2] and df['Low'][-3] > df['donchian_down_n3'][-3]:    # 比较运算符的优先级 > 逻辑与
        return True
    else:
        return False


def close_sell_condition() -> bool: # 空头平仓
    if df['High'][-2] > df['donchian_up_n3'][-2] and df['High'][-3] < df['donchian_up_n3'][-3]:    # 比较运算符的优先级 > 逻辑与
        return True
    else:
        return False
    

#%% 实现功能

# 1. 打印时间戳  
def print_CurrentTime(client):  
    '''返回的是 TWS（本地） 的时间，而不是服务器（server）的时间'''
    # Requests TWS's current time. 
    client.reqCurrentTime()  # 请求函数，读取TWS的时间戳，返回响应函数 currentTime 的结果
    time.sleep(0.5)  # time sleep() 函数推迟调用线程的运行，可通过参数secs指秒数，表示进程挂起的时间。 
    
    
# 2.获取股票和外汇合约信息
def get_ContractDetails(client):
    
    # client.reqMatchingSymbols(0, 'msft')    
    # reqMatchingSymbol() can search ambiguous words 
    # time.sleep(3)   
    # 这个函数官方文档要求至少给出1s来接收响应
    
    
    # 实例化合约
    # EURUSD_contract = FX_Contract("EUR")
    AAPL_contract = Stock_Contract("AAPL")
          
    # 获取合约细节
    client.reqContractDetails(1, EURUSD_contract)
    client.reqContractDetails(1, AAPL_contract)
    
    # Sleep while the request is processed
    time.sleep(5) 
    
 
    
# 3.获取行情信息
def get_MarketData(client):
    
    # 实例化合约
    EURUSD_contract = FX_Contract("EUR")

    # Request ten ticks containing midpoint data
    client.reqTickByTickData(0, EURUSD_contract, 'MidPoint', 10, True)

    # Request market data
    client.reqMktData(1, EURUSD_contract, '', False, False, [])
    # reqMktData 可以请求多于一个合约，可以请求多个多个数据类型
    # 比reqTickByTickData慢，外汇延时5ms，美股期权延时10ms，股票期货及其他延时250ms
    # 每秒钟可请求50个信息


    # Request current bars
    client.reqRealTimeBars(2, EURUSD_contract, 5, 'MIDPOINT', True, [])

    # Request historical bars
    now = datetime.now().strftime("%Y%m%d, %H:%M:%S")
    client.reqHistoricalData(3, EURUSD_contract, now, '2 w', '1 day',
        'MIDPOINT', False, 1, False, [])

    # Request fundamental data
    client.reqFundamentalData(4, EURUSD_contract, 'ReportSnapshot', [])

    # Sleep while the requests are processed
    time.sleep(10)  # 休眠中断，允许价格数据有足够的时间进行传输。
    
# 4. 提交订单及获取账户信息  
def place_Order(client):
    
    # Define a contract for Apple stock
    contract = Stock_Contract('AAPL')
    
    # Define the limit order
    order = Order()
    order.action = 'BUY'
    order.totalQuantity = 200  # 外汇一手是10W
    # order.orderType = 'mkt'  # 订单类型
    order.orderType = 'lmt'  # 订单类型
    order.lmtPrice = 150
    order.transmit = False  # 是否直接 transmit 发送订单

    # Obtain a valid ID for the order
    client.reqIds(1)
    time.sleep(2)

    # Place the order
    if client.order_id:
        client.placeOrder(client.order_id, contract, order)
        time.sleep(5)
    else:
        print('Order ID not received. Ending application.')
        sys.exit()

    # Obtain information about open positions
    client.reqPositions()
    time.sleep(2)

    # Obtain information about account
    client.reqAccountSummary(0, 'All', 'AccountType,AvailableFunds')
    time.sleep(2)
    
    
    print ("数据获取结束，即将断开连接......")


#  每一秒钟打印时间，如果有断连重新链接
def print_Time_Reconnect(client):
    while True:
        if client.isConnected()==False:  
            # 此处需要注意有错误不能退出，不能让程序和市场处在断连的状态
            print (req_current_TWS_time()+"当前无TWS连接！尝试重新连接！")
            
            # 为了避免clientId被占用，启用随机数作为连接clientId
            clientId = np.random.randint(1,100) 
            client = IBapi('127.0.0.1', 7497, clientId)
            time.sleep(1)
            continue 
        else:
            # 当前TWS时间 
            current_TWS_time=req_current_TWS_time()
            current_IDE_time=req_current_time()
            print('Current time is:', current_IDE_time)
            time.sleep(1)


# 隔一段时间获得当前的行情数据并保存下来
def get_historicalData_Store(client):
    eurusd_contract = FX_Contract('EUR')
    while True:
        if ibapi.isConnected()==False:  
            # 此处需要注意有错误不能退出，不能让程序和市场处在断连的状态
            print (req_current_TWS_time()+"当前无TWS连接！尝试重新连接！")
            
            # 为了避免clientId被占用，启用随机数作为连接clientId
            clientId = np.random.randint(1,100) 
            ibapi = IBapi('127.0.0.1', 7497, clientId)
            time.sleep(1)
            continue 
        else:
            # 当前TWS时间 
            current_TWS_time=req_current_TWS_time()
            current_IDE_time=req_current_time()
            print('Current time is:', current_IDE_time)
            
            # 请求历史数据。一般情况下需要更长时间返回，给定3秒钟；其他请求可以酌情减少
            ibapi.reqHistoricalData(reqId=110, contract = eurusd_contract, endDateTime='', durationStr='10 D', \
                                        barSizeSetting='1 hour', whatToShow='bid', useRTH = 1, formatDate=1, \
                                            keepUpToDate=False, chartOptions=[])
            time.sleep(3)
            print('Historical data is retrieved.')
            time.sleep(7)
            
            # 调用自定义函数存储历史数据
            df = ibapi.storehistoricalData()
            df.to_csv('eurusd.csv') 
 
  
def main():
    #%% 连接 TWS
    #连接至本机，本机地址为 127.0.0.1，端口为7497，最后一个参数是客户号码，可以任意
    
    # 之前看到，有这么一个函数，在实例化前面，有什么作用呢？
    # def run_loop():
    # 	client.run()
        
    clientId = np.random.randint(1,100)   # 随机生成客户号码
    
    # Create the client and connect to TWS 创建客户端并连接至 TWS
    client = IBapi('127.0.0.1', 7497, clientId)  # 运行之后，TWS 数据窗口显示连接
   
    if client == -1:
      print ("TWS连接失败")
      return 0 
    
    
    
    print ("已经连接到TWS！")
    
    # 使用 time.sleep 函数来控制程序运行时间，避免运行过快，没有接收到任何返回信息就运行到下一行。
    time.sleep(0.5)  # 持续时间长一点 参数secs指秒数，表示进程挂起的时间, 推迟执行的秒数。
    
    
    #%% 功能实现
    # print_CurrentTime(client)
    
    # get_ContractDetails(client)
    
    get_MarketData(client)
    
    
    
    #%% 断连 TWS
    time.sleep(1)
    print ("即将断开连接")  
    # Disconnect from TWS 
    client.disconnect()  # 断连
    print ("程序执行完成，连接关闭！")  
    
    
    

if __name__ == '__main__':
    main()



   



    
    #Request historical candles
    # ibapi.reqHistoricalData(reqId=110, contract=eurusd_contract, endDateTime='', durationStr='3 D', \
    #                       barSizeSetting='1 hour', whatToShow='bid', useRTH=1, formatDate=1, \
    #                           keepUpToDate=False, chartOptions=[])
    # time.sleep(3) #sleep to allow enough time for data to be returned
    
    
    # if ibapi.historical_data_end==True:
        
    #     print ("请求数据传输完成，存入dataframe中...")
    #     df = pd.DataFrame(ibapi.data, columns=['DateTime','Open','High','Low','Close'])
    #     df['DateTime'] = pd.to_datetime(df['DateTime'])
    #     df.set_index(['DateTime'],inplace=True) 
    #     df.to_csv('EURUSD_Hourly.csv')
        

    # https://interactivebrokers.github.io/tws-api/historical_data.html
    # https://interactivebrokers.github.io/tws-api/classIBApi_1_1EClient.html#aad87a15294377608e59aec1d87420594
    
    # reqID:每次请求的代号 
    # contract金融工具合约
    # endDatetime 从现在开始到过去六个月的某一结束时间 格式为yyyymmdd HH:mm:ss ttt， ttt可选
    # durationStr 从现在开始向前数多长时间，单位可以为 S (seconds), D (days)，W (week)，M (month) 默认为S，注意数字与单位之间有空格
    # barSizeSetting 定义蜡烛图的时间框，可选值为1 sec 5 secs 15 secs 30 secs 1 min 2 mins 3 mins 5 mins 15 mins 30 mins 1 hour 1 day
    # whatToShow 可下载选项 TRADES MIDPOINT BID ASK BID_ASK HISTORICAL_VOLATILITY OPTION_IMPLIED_VOLATILITY
    # useRTH 是否包含常规开盘以外的时刻，0表示包含，1表示不包含
    # formatDate 显示时间格式，1表示yyyymmdd{space}{space}hh:mm:dd格式，2表示长整型格式
    # keepUpToDate 是否下载当前未结束的一根蜡烛图，只能适用于5s以上蜡烛图，此时endDateTime必须设置为""

    # try:
        # df = pd.DataFrame(ibapi.data, columns=['DateTime','Open','High','Low','Close'])
        # df['DateTime'] = pd.to_datetime(df['DateTime'])
        # df.set_index(['DateTime'],inplace=True) 
        # df.to_csv('EURUSD_Hourly.csv') 
        # print(df)
    # except: 
        # print ("dataframe creation error.")
# 获取历史数据，且存入dataframe
    # ibapi.reqHistoricalTicks(18001, eurusd_contract,"20210822 20:00:00", \
    #                          "", 10, "TRADES", 1, True, [])
    # time.sleep(10)
    
    
    ibapi.reqHeadTimeStamp(4101, eurusd_contract, "bid", 0, 1)
    time.sleep(3)



