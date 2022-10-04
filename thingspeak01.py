#-*- coding: utf-8 -*-
import sys

import serial
import time
import signal
import threading
import struct
import requests
from datetime import datetime

# import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# Raspberry Pi pin configuration:
RST = None     # on the PiOLED this pin isnt used

# 128x32 display with hardware I2C:
disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST)

# Initialize library.
disp.begin()

# Clear display.
disp.clear()
disp.display()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
# draw.rectangle((0,0,width,height), outline=0, fill=0)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = 0
top = padding
bottom = height-padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

# Load default font.
# font = ImageFont.load_default()

# Alternatively load a TTF font.  Make sure the .ttf font file is in the same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
font = ImageFont.truetype('font/pixelmix.ttf', 8)

pm_port  = '/dev/ttyAMA1' # 시리얼 포트
gps_port = '/dev/ttyACM0'
pm_baud  = 9600 # 시리얼 보드레이트(통신속도) - Plantower PMS5003/7003
gps_baud = 115200
pm_data_size = 32  # 42(start#1), 4D(start#2), 00 1C(frame length=2*13+2=28/001C), Data#1 ~ Data10,
                # Data11(temp=Data14(Signed)/10), Data12(humidity=Data15/10)
                # Data13H(firmware ver), Data13L(error code), Check Code(start#1+start#2+~+Data13 Low 8 bits)
pm_data_number = 16 # Number of Data
pm_start_chars = 0x424d
api_URL = "https://api.thingspeak.com/update"
update_interval = 5
params = {
    "api_key"   : "N4NJ5OM3GPEQF6BB",
    "timezone"  : "Asia/Seoul",
    "field1"    : 0,                # PM1.0
    "field2"    : 0,                # PM2.5
    "field3"    : 0,                # PM10
    "field4"    : 0,                # Temperature
    "field5"    : 0,                # Humidity
    "field6"    : 0,                # Longitude
    "field7"    : 0,                # Latitude
    "field8"    : 0,                # Altitude
}

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


#쓰레드 종료용 시그널 함수
def handler(signum, frame):
    print("SIGINT(Ctrl-C) Pressed...Exit Thread.")
    exitThread = True

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

    if len(data) != pm_data_number or data[0] != pm_start_chars or checksum != data[-1] or data[14]+2**16 & 0x00ff:
        return -1
    else :
        return 1

def parsing_gps_data(gps_bytes):
    str = gps_bytes.decode('utf-8')
    gps_data = str.rstrip().split(',')
    if check_gps_data(gps_data) == 1:
        return gps_data
    else:
        return -1

# 데이터 체크 함수
def check_gps_data(data):
    # 데이터 길이, start#1, start#2, Check data 검증
    # 상하위바이트 취하기 : 데이터 unsigned화 & 0xff

    return 1

def sendData():
    response = requests.get(api_URL, params=params)
    return response


#본 쓰레드
def readThread(pm_ser, gps_ser):
    global line
    global exitThread

    # 쓰레드 종료될때까지 계속 돌림
    while not exitThread:
        #데이터가 있있다면
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
            # meas_data["pm1"] = None
            # meas_data["pm25"] = None
            # meas_data["pm10"] = None
            # meas_data["temp"] = None
            # meas_data["humi"] = None

        temp = gps_ser.readline()
        gps_data = parsing_gps_data(temp)

        if gps_data == -1: continue
        if gps_data[0] == "$GPRMC" and gps_data[2] == 'A':
            # print(gps_data)
            # data = parsing_gps_data(str)
            # if data == -1 : break
            meas_data["long"] = gps_data[3]
            meas_data["lati"] = gps_data[5]

        else:
            gps_ser.flushInput()
            # meas_data["long"] = None
            # meas_data["lati"] = None

        meas_data["timestamp"] = time.time()

        if None not in meas_data.values():
            print(meas_data)
        # print(meas_data)
        time.sleep(1)

if __name__ == "__main__":
    #종료 시그널 등록
    signal.signal(signal.SIGINT, handler)

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
            params["field1"] = meas_data["pm1"]
            params["field2"] = meas_data["pm25"]
            params["field3"] = meas_data["pm10"]
            params["field4"] = meas_data["temp"]
            params["field5"] = meas_data["humi"]
            params["field6"] = meas_data["long"]
            params["field7"] = meas_data["lati"]
            params["field8"] = meas_data["timestamp"]

            if None in [params["field1"], params["field2"], params["field3"], params["field4"], params["field5"]]:
                pm_status = 0
            else:
                pm_status = 1

            if None in [params["field6"], params["field7"]]:
                gps_status = 0
            else:
                gps_status = 1

            if pm_status == 1 and gps_status == 1:
                res = sendData()
                print("Data ready and sent", res.status_code, res.text, ' :', meas_data)
            else:
                if pm_status == 0:
                    msg_status += " PM"
                if gps_status == 0:
                    msg_status += " GPS"
                print(msg_status, ':', meas_data)
            # if None not in meas_data.values():
            #     print(sendData())

            _date = datetime.fromtimestamp(int(meas_data["timestamp"])).strftime('%m-%d %H:%M')

            # Draw a black filled box to clear the image.
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            draw.text((x, top),      "PM1.0: %4s / PM2.5: %4s" \
                      % ("NA" if meas_data["pm1"] is None else str(meas_data["pm1"]), "NA" if meas_data["pm25"] is None else str(meas_data["pm25"])), font=font, fill=255)
            draw.text((x, top + 8),  "PM 10: %4s / %11s" \
                      % ("NA" if meas_data["pm10"] is None else str(meas_data["pm10"]), _date), font=font, fill=255)
            draw.text((x, top + 16), "Temp:  %4s / Humi:  %4s" \
                      % ("NA" if meas_data["temp"] is None else str(meas_data["temp"]), "NA" if meas_data["humi"] is None else str(meas_data["humi"])), font=font, fill=255)
            draw.text((x, top + 24), "LON: %6s / LAT: %6s" \
                      % ("NA" if meas_data["long"] is None else str(meas_data["long"]), "NA" if meas_data["lati"] is None else str(meas_data["lati"])), font=font, fill=255)

            # Display image.
            disp.image(image)
            disp.display()

            time.sleep(update_interval)
    except KeyboardInterrupt:
        print("Stop Measuring...")
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        sys.exit()
