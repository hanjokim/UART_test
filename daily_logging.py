# -*- coding: utf-8 -*-
import os

# import requests
# import signal

import configparser
import sys
import serial
import time
import threading
import struct
from datetime import datetime
from datetime import timedelta
# import logging
import logging.handlers

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306,  sh1106

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

conf_values = configparser.ConfigParser()
conf_values.read('config.ini')
general = conf_values['GENERAL']
pm = conf_values['PM']
gps = conf_values['GPS']

pm_port = pm['pm_port']
gps_port = gps['gps_port']

pm_baud = pm.getint('pm_baud')
gps_baud = gps.getint('gps_baud')

pm_timeout = pm.getfloat('pm_timeout')
gps_timeout = gps.getfloat('gps_timeout')

pm_data_size = pm.getint('pm_data_size')
pm_data_number = pm.getint('pm_data_number')
pm_start_chars = int(pm['pm_start_chars'], 16)
is_PMS7003T = pm.getboolean('is_PMS7003T')
oled_driver = general['oled']
disp_rotate = int(general['disp_rotate'])

update_interval = general.getfloat('update_interval')
thread_interval = general.getfloat('thread_interval')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
timedfilehandler = logging.handlers.TimedRotatingFileHandler(filename='log/finedustlog', when='midnight', interval=1, encoding='utf-8', utc=False)
# timedfilehandler.setFormatter(formatter)
timedfilehandler.suffix = "%Y%m%d"

logger.addHandler(timedfilehandler)
meas_data = {
    "pm1"   : None,
    "pm25"  : None,
    "pm10"  : None,
    "temp"  : None,
    "humi"  : None,
    "long"  : None,
    "lati"  : None,
    "timestamp"  : None,
}

exitThread = False   # 쓰레드 종료용 변수
clock_set = False

device = None

try:
    iface = i2c(port=1, address=0x3C)
    if oled_driver == 'ssd1306':
        device = ssd1306(iface, rotate=disp_rotate)
    elif oled_driver == 'sh1106':
        device = sh1106(iface, rotate=disp_rotate)
    else:
        print("OLED driver configuration error in config.ini")
        sys.exit()
except Exception as e:
    print("Display device initialization error:", e)
    sys.exit()

width = device.width
height = device.height
padding = 0
top = padding
bottom = height - padding
x = 0

# font = ImageFont.load_default()
font = ImageFont.truetype('font/Hack.ttf', 10)

def disp_OLED(meas_data):
    with canvas(device) as draw:
        draw.rectangle((0, 0, width-1, height-1), outline=0, fill=0)
        draw.text((x, top), "%19s" % meas_data['timestamp'] if meas_data['timestamp'] else "Waiting for data...", font=font, fill=255)
        draw.text((x, top + 10), "PM1/2.5/10:%-3s/%-3s/%-3s" % (str(meas_data["pm1"] if meas_data["pm1"] else "-"),
             str(meas_data["pm25"] if meas_data["pm25"] else "-"), str(meas_data["pm10"] if meas_data["pm10"] else "-")), font=font, fill=255)
        draw.text((x, top + 20), "Temp: %-4s'C" % str(meas_data["temp"] if meas_data["temp"] else "-"), font=font, fill=255)
        draw.text((x, top + 30), "Humi: %-4s %%" % str(meas_data["humi"] if meas_data["humi"] else "-"), font=font, fill=255)
        draw.text((x, top + 40), "Long: %-10s" % str(meas_data["long"] if meas_data["long"] else "-"), font=font, fill=255)
        draw.text((x, top + 50), "Lati: %-10s" % str(meas_data["lati"] if meas_data["lati"] else "-"), font=font, fill=255)

# 데이터 처리할 함수
def parsing_pm_data(packed_data):
    tmp = struct.unpack('!16h', packed_data)
    print(tmp)
    if check_pm_data(tmp) == 1:
        return tmp
    else:
        return -1

# 데이터 체크 함수
def check_pm_data(data):
    # 데이터 길이, start#1, start#2, Check data 검증
    # 상하위바이트 취하기 : 데이터 unsigned화 & 0xff
    checksum = 0
    for i, v in enumerate(data):
        if i != len(data) - 1:
            checksum += (((v+2**16) & 0xff00) >> 8) + (v+2**16 & 0x00ff)

    if len(data) == pm_data_number and data[0] == pm_start_chars and checksum == data[-1] and data[14] & 0x00ff == 0x00:
        return 1
    else :
        return -1

def parsing_gps_data(gps_bytes):
    try:
        str = gps_bytes.decode('utf-8')
        gps_data = str.rstrip().split(',')
        if check_gps_data(gps_data) == 1:
            # print(gps_data)
            return gps_data
        else:
            return -1
    except UnicodeDecodeError:
        return -1


# 데이터 체크 함수
def check_gps_data(data):
    if '$GPRMC' in data:
        return 1
    else:
        return -1

#본 쓰레드
def readThread(pm_ser, gps_ser):
    global line
    global exitThread
    global clock_set

    # 쓰레드 종료될때까지 계속 돌림
    while not exitThread:
        temp = pm_ser.readline(pm_data_size)

        if len(temp) == pm_data_size:
            pm_data = parsing_pm_data(temp)
            if pm_data != -1:
                # continue
                meas_data["pm1"] = pm_data[2]
                meas_data["pm25"] = pm_data[3]
                meas_data["pm10"] = pm_data[4]
                meas_data["temp"] = (pm_data[12] / 10.) if is_PMS7003T else None
                meas_data["humi"] = (pm_data[13] / 10.) if is_PMS7003T else None
        else:
            pm_ser.flushInput()

        temp = gps_ser.readline()
        gps_data = parsing_gps_data(temp)

        if gps_data != -1 and len(gps_data) >= 3:
            if gps_data[0] == "$GPRMC" and gps_data[2] == 'A':
                if gps_data[1] and gps_data[9]:
                    dt_str = datetime.strptime(gps_data[1][0:6] + gps_data[9], '%H%M%S%d%m%y') - timedelta(hours=-9)
                    if clock_set is False:
                        res = os.system("sudo date -s \'%s\'" % dt_str.strftime('%Y-%m-%d %H:%M:%S'))
                        if res == 0:
                            clock_set = True
                meas_data["long"] = float(gps_data[3]) if gps_data[3] else None
                meas_data["lati"] = float(gps_data[5]) if gps_data[5] else None

        else:
            gps_ser.flushInput()

        # meas_data["timestamp"] = time.time()
        meas_data["timestamp"] = datetime.now().strftime('%Y/%m/%d %H:%M:%S')

        time.sleep(thread_interval)

if __name__ == "__main__":
    #시리얼 열기
    pm_ser = serial.Serial(pm_port, pm_baud, timeout=pm_timeout)
    gps_ser = serial.Serial(gps_port, gps_baud, timeout=gps_timeout)

    #시리얼 읽을 쓰레드 생성
    thread = threading.Thread(target=readThread, args=(pm_ser, gps_ser, ))

    #시작!
    thread.start()

    pm_status = 0
    gps_status = 0

    try:
        while True:
            msg_status = "Not ready"

            if None in [meas_data["pm1"], meas_data["pm25"], meas_data["pm10"], meas_data["temp"], meas_data["humi"]]:
                pm_status = 0
            else:
                pm_status = 1

            if None in [meas_data["long"], meas_data["lati"]]:
                gps_status = 0
            else:
                gps_status = 1

            # dtstring = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
            dtstring = meas_data['timestamp']

            if pm_status == 1 and gps_status == 1:
                # res = sendData() --> logging
                logger.info("%s,%f,%f,%f,%f,%f,%f,%f",
                            dtstring,
                            meas_data["pm1"], meas_data["pm25"], meas_data["pm10"], meas_data["temp"], meas_data["humi"],
                            meas_data["long"], meas_data["lati"])
                print("Logged @%s -" % meas_data)
            else:
                if pm_status == 0:
                    msg_status += " PM"
                if gps_status == 0:
                    msg_status += " GPS"
                print(msg_status, dtstring, '-', meas_data)

            # _dt = datetime.fromtimestamp(int(meas_data["timestamp"])).strftime('%Y-%m-%d %H:%M:%S')

            disp_OLED(meas_data)

            meas_data["pm1"]        = None
            meas_data["pm25"]       = None
            meas_data["pm10"]       = None
            meas_data["temp"]       = None
            meas_data["humi"]       = None
            meas_data["long"]       = None
            meas_data["lati"]       = None
            meas_data["timestamp"]  = None

            time.sleep(update_interval)
    except KeyboardInterrupt:
        print("Stop Measuring...")
        exitThread = 1
        device.hide()
        pm_ser.close()
        gps_ser.close()
        sys.exit()
