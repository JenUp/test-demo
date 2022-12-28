# 导入EClinet类，用于从客户端向服务器发送信息
from ibapi.client import EClient

# 引用合约类 Contract，Contract类用于创建合约使用
from ibapi.client import Contract

# 导入EWrapper类，用于接收服务器向客户端发送的信息 
from ibapi.wrapper import EWrapper 

# 导入 threading 模块的 Thread 类，用于开启多线程功能
from threading import Thread  

# iswrapper 用来重构 EWrapper 下的所有函数的
from ibapi.utils import iswrapper

# 导入时间库，用于后续停时使用，延迟控制
import time

# 导入日期时间库，用于后续本机时间的获取、修改时间格式
from datetime import datetime  


class IBapi(EClient, EWrapper):  # 类的继承：IB核心是多继承，同时继承 EClient 和 EWrapper
    def __init__(self, addr, port, client_id):  # 每次连接，需要自动设置一些基本参数
        
        # EClient 构造方法
        EClient. __init__(self, self)  
         
        # 继承自 EClient, 创建连接
        self.connect(addr, port, client_id)  
        
        # 开启多线程任务
        thread = Thread(target = self.run)
        thread.start()
    
        
    #%% 3. 获取行情信息
    @iswrapper
    def tickPrice(self, reqId, field, price, attribs):
        '''reqMktData 的响应函数  '''
        print('tick价格 - 字段: {}, 价格: {}'.format(field, price))
        

    @iswrapper
    def tickSize(self, reqId, field, size):
        ''' reqMktData 的响应函数 '''
        print('tick交易量 - 字段: {}, 交易量: {}'.format(field, size))
    
    
    @iswrapper
    def tickByTickMidPoint(self, reqId, tick_time, midpoint):
        ''' reqTickByTickData 的响应函数 '''
        print('tick报价中间值: {}'.format(midpoint))


    @iswrapper
    def realtimeBar(self, reqId, time, open, high, low, close, volume, WAP, count):
        ''' reqRealTimeBars 的响应函数  '''
        print('实时蜡烛图 - 开盘价格: {}'.format(open))

    @iswrapper
    def historicalData(self, reqId, bar):
        ''' reqHistoricalData 的响应函数 '''
        print('历史数据 - 收盘价格: {}'.format(bar.close))
        
    
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

def main():
    
    #连接至本机，本机地址为 127.0.0.1，端口为7497，最后一个参数是客户号码，可以任意
    client = IBapi('127.0.0.1', 7497, 2)  # 运行之后，TWS 数据窗口显示连接
    
    # 实现功能：确认连接
    print ("已经连接到TWS！")
    # 使用 time.sleep 函数来控制程序运行时间
    time.sleep(0.5)  
    
    # 创建外汇合约，以美元欧元货币对为例
    EUR_contract = FX_Contract("EUR")
    
    # 获取实时市场数据
    print ("============ 实时市场数据 ============")
    # 常用市场数据（Top Market Data）
    print ("【1. 常用市场数据】")
    # 监控列表数据（Watchlist Data）
    print ("【1.1 监控列表数据】")
    client.reqMktData(1, EUR_contract, '', False, False, [])
    time.sleep(30)
    
    # 逐笔成交数据   
    print ("\n【1.2 逐笔成交数据】")
    client.reqTickByTickData(0, EUR_contract, 'MidPoint', 10, True)
    time.sleep(30)
    
    # 5秒实时柱状图数据
    print ("\n【2. 5秒实时柱状图数据】")
    client.reqRealTimeBars(2, EUR_contract, 5, 'MIDPOINT', True, [])
    time.sleep(30)
    
    # 历史市场数据：历史美国线数据（historical bar data）
    print ("\n============ 历史市场数据 ============")
    now = datetime.now().strftime("%Y%m%d, %H:%M:%S")
    client.reqHistoricalData(3, EUR_contract, now, '2 w', '1 day','MIDPOINT', False, 1, False, [])
    time.sleep(30)

    # 断连 TWS
    print ("\n即将断开连接")  
    client.disconnect()  # 断连
    print ("程序执行完成，连接关闭！")  
    

if __name__ == '__main__':
    main()