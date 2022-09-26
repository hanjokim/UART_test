#-*- coding: utf-8 -*-

import serial
import time
import signal
import threading
import struct
import requests


line = [] #라인 단위로 데이터 가져올 리스트 변수

port = '/dev/ttyAMA1' # 시리얼 포트
baud = 9600 # 시리얼 보드레이트(통신속도) - Plantower PMS5003/7003
data_size = 32  # 42(start#1), 4D(start#2), 00 1C(frame length=2*13+2=28/001C), Data#1 ~ Data10,
                # Data11(temp=Data14(Signed)/10), Data12(humidity=Data15/10)
                # Data13H(firmware ver), Data13L(error code), Check Code(start#1+start#2+~+Data13 Low 8 bits)
data_number = 18 # Number of Data
start1 = 0x42
start2 = 0x4d
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
    "field8"    : 0,                # Altitude
}

exitThread = False   # 쓰레드 종료용 변수


#쓰레드 종료용 시그널 함수
def handler(signum, frame):
     exitThread = True

#데이터 처리할 함수
def parsing_data(data):
    tmp = struct.unpack('!bb13h2ch', data)
    if check_data(tmp) == 1:
        return tmp
    else:
        return -1

#데이터 체크 함수
def check_data(data):
    #데이터 길이, start#1, start#2, Check data 검증
    #하위바이트 취하기 : 데이터 & 0x0f
    checksum = 0
    for i in data:
        checksum += i if type(i) == int else i[0]

    print(checksum, data[-1])

    if len(data) != data_number or data[0] != start1 or data[1] != start2:
        return -1
    else :
        return 1

def sendData():
    response = requests.get(api_URL, params=params)
    return response


#본 쓰레드
def readThread(ser):
    global line
    global exitThread

    # 쓰레드 종료될때까지 계속 돌림
    while not exitThread:
        #데이터가 있있다면
        temp = ser.readline(data_size)
        if len(temp) == data_size:
            data = parsing_data(temp)
            print(data)
        else:
            ser.flushInput()
        time.sleep(1)

if __name__ == "__main__":
    #종료 시그널 등록
    signal.signal(signal.SIGINT, handler)

    #시리얼 열기
    ser = serial.Serial(port, baud, timeout=0)

    #시리얼 읽을 쓰레드 생성
    thread = threading.Thread(target=readThread, args=(ser,))

    #시작!
    thread.start()

    sendData()