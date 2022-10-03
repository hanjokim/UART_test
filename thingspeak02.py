#-*- coding: utf-8 -*-

import serial
import time
import signal
import threading
import struct
import requests
# from datetime import datetime


gps_port = '/dev/ttyACM0'
gps_baud = 115200
api_URL = "https://api.thingspeak.com/update"
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
    "field8"    : 0,                # timestamp
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
     exitThread = True

# 데이터 처리할 함수
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
    # checksum = 0
    # for i, v in enumerate(data):
    #     if i != len(data) - 1:
    #         checksum += (((v+2**16) & 0xff00) >> 8) + (v+2**16 & 0x00ff)
    #
    # if len(data) != 0:
    #     return -1
    # else :
    #     return 1
    return 1

def sendData():
    response = requests.get(api_URL, params=params)
    return response


#본 쓰레드
def readThread(gps_ser):
    global exitThread

    # 쓰레드 종료될때까지 계속 돌림
    while not exitThread:
        #데이터가 있있다면
        temp = gps_ser.readline()
        gps_data = parsing_gps_data(temp)
        # print(temp)
        if gps_data == -1: continue
        if gps_data[0] == "$GPRMC" and gps_data[2] == 'A':
            print(gps_data)
            # data = parsing_gps_data(str)
            # if data == -1 : break
            meas_data["long"] = gps_data[3]
            meas_data["lati"] = gps_data[5]
            # meas_data["timestamp"] = time.time()

            print(meas_data)
        else:
            gps_ser.flushInput()
            meas_data["long"] = None
            meas_data["lati"] = None
        time.sleep(1)

if __name__ == "__main__":
    #종료 시그널 등록
    signal.signal(signal.SIGINT, handler)

    #시리얼 열기
    gps_ser = serial.Serial(gps_port, gps_baud, timeout=0)

    #시리얼 읽을 쓰레드 생성
    thread = threading.Thread(target=readThread, args=(gps_ser, ))

    #시작!
    thread.start()

    # sendData()