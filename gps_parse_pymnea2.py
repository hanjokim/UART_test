import io

import pynmea2
import serial


ser = serial.Serial('/dev/cu.usbserial-A50285BI', 9600, timeout=1)
sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))

while 1:
    try:
        line = sio.readline()
        msg = pynmea2.parse(line)
        if 'RMC' in msg.identifier():
            print(msg.fields, msg.status, msg.is_valid, msg.latitude, msg.lat_dir, msg.longitude, msg.lon_dir, msg.datetime)
            print(dir(msg))
        # print(repr(msg))
    except serial.SerialException as e:
        print('Device error: {}'.format(e))
        break
    except pynmea2.ParseError as e:
        print('Parse error: {}'.format(e))
        continue
