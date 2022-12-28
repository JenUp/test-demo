# import ib_insync


# # util.startLoop()


import numpy as np

from ib_insync import *
ib=IB()

clientId=np.random.randint(0,32)
ib.connect(clientId=clientId)

# ib.positions()
# ib.sleep(30)
# ib.disconnect()