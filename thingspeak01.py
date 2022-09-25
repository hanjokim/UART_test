#-*- coding: utf-8 -*-
# https://blog.naver.com/PostView.naver?isHttpsRedirect=true&blogId=chandong83&logNo=220941128858

import serial
import time
import signal
import threading
import struct


line = [] #라인 단위로 데이터 가져올 리스트 변수

port = '/dev/ttyAMA1' # 시리얼 포트
baud = 9600 # 시리얼 보드레이트(통신속도) - Plantower PMS5003/7003
data_size = 32  # 42(start#1), 4D(start#2), 00 1C(frame length=2*13+2=28/001C), Data#1 ~ Data10,
                # Data11(temp=Data14(Signed)/10), Data12(humidity=Data15/10)
                # Data13H(firmware ver), Data13L(error code), Check Code(start#1+start#2+~+Data13 Low 8 bits)

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

    if len(data) != 18 or data[0] != 0x42 or data[1] != 0x4d:
        return -1
    else :
        return 1



#본 쓰레드
def readThread(ser):
    global line
    global exitThread

    # 쓰레드 종료될때까지 계속 돌림
    while not exitThread:
        #데이터가 있있다면
        temp = ser.readline(data_size)
        if len(temp) == 32:
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