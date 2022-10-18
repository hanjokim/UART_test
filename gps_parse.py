import os
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
        print(os.system('sudo date -s \"%s\"' % dt.strftime('%Y-%m-%d %H:%M:%S')))
        print(os.system('sudo timedatectl set-ntp 0'))
        print(os.system('sudo timedatectl set-time \"%s\"' % dt.strftime('%Y-%m-%d %H:%M:%S')))
        print(os.system('sudo timedatectl set-ntp 1'))
