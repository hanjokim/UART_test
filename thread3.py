#-*- coding: utf-8 -*-
import serial
import time
import signal
import threading


line = [] #라인 단위로 데이터 가져올 리스트 변수

# port = 'COM3'# 시리얼 포트
port = '/dev/ttyAMA1' # 시리얼 포트
baud = 9600 # 시리얼 보드레이트(통신속도)
STX = 0x02
ETX = 0x03

exitThread = False   # 쓰레드 종료용 변수


#쓰레드 종료용 시그널 함수
def handler(signum, frame):
    print("Exit handler enabled")
    exitThread = True


#데이터 처리할 함수
def parsing_data(data):
    # 리스트 구조로 들어 왔기 때문에
    # 작업하기 편하게 스트링으로 합침
    tmp = ''.join(data)

    #출력!
    print("Data: ", data, tmp, tmp.encode())


#본 쓰레드
def readThread(ser):
    global line
    global exitThread

    # 쓰레드 종료될때까지 계속 돌림
    while not exitThread:
        #데이터가 있있다면
        for c in ser.read():
            #line 변수에 차곡차곡 추가하여 넣는다.
            line.append(chr(c))
            # print(c, chr(c), ord(b'\x03'), c==ord('\x03'))
            if c == ETX: #라인의 끝을 만나면..
                #데이터 처리 함수로 호출
                parsing_data(line)

                #line 변수 초기화
                del line[:]

if __name__ == "__main__":
    #종료 시그널 등록
    signal.signal(signal.SIGINT, handler)

    #시리얼 열기
    ser = serial.Serial(port=port, baudrate=baud, timeout=1)

    #시리얼 읽을 쓰레드 생성
    thread = threading.Thread(target=readThread, args=(ser,))

    #시작!
    thread.start()