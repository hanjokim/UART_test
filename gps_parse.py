from datetime import datetime
from datetime import timedelta
from serial import Serial
from pynmeagps import NMEAReader
stream = Serial('/dev/ttyACM0', 9600, timeout=3)
nmr = NMEAReader(stream)
while True:
    (_r, _data) = nmr.read()
    if _data.msgID == "RMC":
        _dt = str(_data.date) + ' ' + str(_data.time)
        dt = datetime.strptime(_dt, '%Y-%m-%d %H:%M:%S') - timedelta(hours=-9)
        print(dt)
        print(_data)