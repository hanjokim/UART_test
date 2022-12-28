import io
import time
from datetime import datetime
from datetime import timedelta

import pynmea2
import serial


ser = serial.Serial('/dev/ttyAMA1', 9600, timeout=1)                      # RPi GPIO
# ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)                      # RPi U-blox7
# ser = serial.Serial('/dev/cu.usbserial-A50285BI', 9600, timeout=1)      # Mac USB-FTDI
sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))

streamreader = pynmea2.NMEAStreamReader(sio, 'ignore')
while 1:
    try:
        for msg in streamreader.next():
            if 'RMC' in msg.identifier():
                print(msg.fields, msg.timestamp, msg.datestamp)
                print(msg.latitude,  msg.latitude_minutes,  msg.latitude_seconds,  msg.longitude,  msg.longitude_minutes,  msg.longitude_seconds)
                print(dir(msg))
    except UnicodeDecodeError as e:
        print("Error: {}".format(e))
        continue