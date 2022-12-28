from threading import Thread
import sys
import time

from ibapi.client import EClient, Contract
from ibapi.order import Order
from ibapi.wrapper import EWrapper
from ibapi.utils import iswrapper

class IBapi(EWrapper, EClient): # 类的继承：多继承，同时继承 EClient 和 EWrapper
    
    def __init__(self, addr, port, client_id): # 每次连接，需要自动设置一些基本参数
        EClient.__init__(self, self)
        
    # TWS 连接
        self.connect(addr, port, client_id)

        # 开启客户端线程
        thread = Thread(target = self.run)
        thread.start()
    
    @iswrapper
    def nextValidId(self, order_id):
        # 返回下一个可用的订单编码
        self.order_id = order_id
        print('Order ID：', order_id)
        
    @iswrapper
    def openOrder(self,order_id, contract, order, state):
        # 
        print('Order status:{}'.format(state.status))
        print('Commission charged:{}'.format(state.commission))
    
    @iswrapper
    def orderStatus(self, order_id, status, filled, remaining, avgFillPrice, \
                    permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
       #
        print('Number of filled positions: {}'.format(filled))
        print('Average fill price: {}'.format(avgFillPrice))


client = IBapi('127.0.0.1', 7497,5)  # 运行之后，显示连接
print ("已经连接到TWS！")
time.sleep(2)  # 持续时间长一点 参数secs指秒数，表示进程挂起的时间, 推迟执行的秒数。

# 创建合约对象
contract = Contract()  # 实例化 Contract 类
contract.symbol = 'EUR'  # 代码  
contract.secType =  'CASH'  # 证券类型 Security type
contract.currency = "USD"  # 货币
contract.exchange = 'IDEALPRO'  # 交易所

# 创建合约对象
# eurusd_contract = FX_Contract("EUR")

# 定义订单
order = Order()
order.action = 'sell'
order.totalQuantity = 20000  # 外汇一手是10W
# order.orderType = 'mkt'  # 订单类型
order.orderType = 'lmt'  # 订单类型
order.lmtPrice = 1.1900
order.transmit = True  # 是否直接 transmit 发送订单\

client.reqIds(100)  # reqIds() 接收的参数为任意整数
# 服务器返回一个当前可以用的订单编码（最小的编码） 编号需要有唯一性→ nextValidID
time.sleep(2)

if client.order_id:
    client.placeOrder(client.order_id, contract, order)
    time.sleep(2)
else:
    print('Order ID not received. Ending application.')
    sys.exit()

time.sleep(1)
client.disconnect()  # 断连， 需要重启 kernel 
print ("程序执行完成，连接关闭！")