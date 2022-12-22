import io
import time
from datetime import datetime
from datetime import timedelta

import pynmea2
import serial


ser = serial.Serial('/dev/ttyAMA2', 9600, timeout=1)                      # RPi GPIO
# ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)                      # RPi U-blox7
# ser = serial.Serial('/dev/cu.usbserial-A50285BI', 9600, timeout=1)      # Mac USB-FTDI
sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))

while 1:
    try:
        line = sio.readline()
        print(line)
        msg = pynmea2.parse(line)
        print(msg)
        if 'RMC' in msg.identifier():
            print(msg)
            print(msg.status, msg.is_valid, msg.latitude, msg.lat_dir, msg.longitude, msg.lon_dir)
            # dt = msg.datetime - timedelta(hours=-9)
            # print(dt)
            print(str(msg).split(','))
    except serial.SerialException as e:
        print('Device error: {}'.format(e))
        break
    except pynmea2.ParseError as e:
        print('Parse error: {}'.format(e))
        continue
