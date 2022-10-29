#-*- coding: utf-8 -*-
import os

import requests
import signal

import sys
import serial
import time
import threading
import struct
from datetime import datetime
from datetime import timedelta
import logging
import logging.handlers

import board, busio
import adafruit_ssd1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

pm_port  = '/dev/ttyAMA1' # 시리얼 포트
gps_port = '/dev/ttyAMA2' # GPS on UART TXD3/RXD3 pin 7/29
# gps_port = '/dev/ttyACM0' # GPS on USB

pm_baud  = 9600 # 시리얼 보드레이트(통신속도) - Plantower PMS5003/7003
gps_baud = 9600
pm_data_size = 32  # 42(start#1), 4D(start#2), 00 1C(frame length=2*13+2=28/001C), Data#1 ~ Data10,
                # Data11(temp=Data14(Signed)/10), Data12(humidity=Data15/10)
                # Data13H(firmware ver), Data13L(error code), Check Code(start#1+start#2+~+Data13 Low 8 bits)
pm_data_number = 16 # Number of Data
pm_start_chars = 0x424d

update_interval = 10

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
    "timestamp"  : 0.,
}

exitThread = False   # 쓰레드 종료용 변수
clock_set = False

# OLED display initialization
i2c = busio.I2C(board.SCL, board.SDA)
disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, addr=0x3c)
disp.fill(0)
disp.show()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

padding = 0
top = padding
bottom = height-padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

# font = ImageFont.load_default()
font = ImageFont.truetype('font/pixelmix.ttf', 8)

def disp_OLED(meas_data, dt):
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((x, top), "PM1.0: %4s / PM2.5: %4s" \
              % ("NA" if meas_data["pm1"] is None else str(meas_data["pm1"]),
                 "NA" if meas_data["pm25"] is None else str(meas_data["pm25"])), font=font, fill=255)
    draw.text((x, top + 8), "PM10: %4s %11s" \
              % ("NA" if meas_data["pm10"] is None else str(meas_data["pm10"]), dt), font=font, fill=255)
    draw.text((x, top + 16), "Temp:  %4s / Humi:  %4s" \
              % ("NA" if meas_data["temp"] is None else str(meas_data["temp"]),
                 "NA" if meas_data["humi"] is None else str(meas_data["humi"])), font=font, fill=255)
    draw.text((x, top + 24), "LO: %7s / LA: %7s" \
              % ("NA" if meas_data["long"] is None else str(meas_data["long"])[0:8],
                 "NA" if meas_data["lati"] is None else str(meas_data["lati"])[0:8]), font=font, fill=255)

    # Display image.
    disp.image(image)
    # disp.display()
    disp.show()


# 데이터 처리할 함수
def parsing_pm_data(packed_data):
    tmp = struct.unpack('!16h', packed_data)
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

    if len(data) == pm_data_number and data[0] == pm_start_chars or checksum == data[-1] and data[14] & 0x00ff == 0x00:
        return 1
    else :
        return -1

def parsing_gps_data(gps_bytes):
    try:
        str = gps_bytes.decode('utf-8')
        gps_data = str.rstrip().split(',')
        if check_gps_data(gps_data) == 1:
            # print("gps data check ok")
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
            if pm_data == -1: continue
            meas_data["pm1"] = pm_data[2]
            meas_data["pm25"] = pm_data[3]
            meas_data["pm10"] = pm_data[4]
            meas_data["temp"] = pm_data[12] / 10.
            meas_data["humi"] = pm_data[13] / 10.
        else:
            pm_ser.flushInput()

        temp = gps_ser.readline()
        gps_data = parsing_gps_data(temp)

        if gps_data == -1 or len(gps_data) < 3: continue
        if gps_data[0] == "$GPRMC" and gps_data[2] == 'A':
            if gps_data[1] is not None and gps_data[9] is not None:
                dt_str = datetime.strptime(gps_data[1][0:6] + gps_data[9], '%H%M%S%d%m%y') - timedelta(hours=-9)
                # print(_td_str, dt_str, dt_str.strftime('%Y-%m-%d %H:%M:%S'))
                if clock_set is False:
                    res = os.system("sudo date -s \'%s\'" % dt_str.strftime('%Y-%m-%d %H:%M:%S'))
                    if res == 0:
                        clock_set = True
            meas_data["long"] = float(gps_data[3]) if gps_data[3] is not None else None
            meas_data["lati"] = float(gps_data[5]) if gps_data[5] is not None else None

        else:
            gps_ser.flushInput()

        meas_data["timestamp"] = time.time()

        time.sleep(1)

if __name__ == "__main__":
    #시리얼 열기
    pm_ser = serial.Serial(pm_port, pm_baud, timeout=0)
    gps_ser = serial.Serial(gps_port, gps_baud, timeout=0)

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

            if pm_status == 1 and gps_status == 1:
                # res = sendData() --> logging
                dtstring = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
                logger.info("%s,%f,%f,%f,%f,%f,%f,%f,%f",
                            dtstring,
                            meas_data["pm1"], meas_data["pm25"], meas_data["pm10"], meas_data["temp"], meas_data["humi"],
                            meas_data["long"], meas_data["lati"], meas_data["timestamp"])
                print("Logged @%s -" % dtstring, meas_data)
            else:
                if pm_status == 0:
                    msg_status += " PM"
                if gps_status == 0:
                    msg_status += " GPS"
                print(msg_status, '-', meas_data)

            _dt = datetime.fromtimestamp(int(meas_data["timestamp"])).strftime('%m-%d %H:%M:%S')

            disp_OLED(meas_data, _dt)

            meas_data["pm1"]        = None
            meas_data["pm25"]       = None
            meas_data["pm10"]       = None
            meas_data["temp"]       = None
            meas_data["humi"]       = None
            meas_data["long"]       = None
            meas_data["lati"]       = None
            meas_data["timestamp"]  = 0

            time.sleep(update_interval)
    except KeyboardInterrupt:
        print("Stop Measuring...")
        exitThread = 1
        disp.fill(0)
        disp.show()
        # time.sleep(1)
        pm_ser.close()
        gps_ser.close()
        sys.exit()
