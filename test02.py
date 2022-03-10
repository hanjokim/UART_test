# Raspberry Pi 와 PC Serial 통신
# https://post.naver.com/viewer/postView.nhn?volumeNo=31531516&memberNo=2534901

import serial
import time
import threading

DEV_PLATFORM = 'PI4'

if DEV_PLATFORM == 'WIN':
    port = 'COM5'
elif DEV_PLATFORM == 'PI3':
    port = '/dev/ttyAMA0'
else:
    port = '/dev/ttyAMA1'

baud = 115200  # serial speed

ser = serial.Serial(
    port=port,
    baudrate=baud,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1
)

line = ''
alive = True
endcommand = False


# 쓰레드
def readthread(ser):
    global line
    global alive
    global endcommand

    print('readthread init')

    while alive:
        try:
            for c in ser.read():
                line += (chr(c))
                if line.startswith('['):
                    if line.endswith(']'):
                        print('receive data=' + line)
                        if line == '[end]':
                            endcommand = True
                            print('end command\n')
                        # line reset
                        line = ''
                        ser.write('ok'.encode())
                else:
                    # print("Not a valid command:", line)
                    line = ''
        except Exception as e:
            print('read exception')

    print('thread exit')

    ser.close()


def main():
    global endcommand
    global alive

    # 시리얼 쓰레드 생성
    thread = threading.Thread(target=readthread, args=(ser,))
    thread.daemon = True
    thread.start()

    if DEV_PLATFORM == 'DESKTOP':
        for count in range(0, 10):
            strcmd = '[test' + str(count) + ']'
            print('send data=' + strcmd)
            strencoding = strcmd.encode()
            ser.write(strencoding)
            time.sleep(1)

        strcmd = '[end]'
        ser.write(strcmd.encode())
        print('send data=' + strcmd)

    else:
        while True:
            time.sleep(1)
            if endcommand is True:
                break

    alive = False
    print('main exit')
    time.sleep(1)
    exit()


main()