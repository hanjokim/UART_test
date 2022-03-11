# http://www.acronet.kr/25488

import time
import serial
import select
import sys

# 특정 시간 동안 입력이 없으면 timeout (리눅스 계열용, 윈도우즈용은 댓글 참조)
def input_with_timeout(prompt, timeout):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    ready, _, _ = select.select([sys.stdin], [],[], timeout)
    if ready:
        return sys.stdin.readline().rstrip('\n') # expect stdin to be line-buffered
    return None


try:
    # Serial port setup
    ser = serial.Serial(
        port='/dev/ttyAMA1', # Raspberry pi 3B+ GPIO, Windows에서는 COM3 형태로 입력
        baudrate = 115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
        )

    print("Loop until press 'Ctrl+C' or Receive 'exit' from serial port")

    while True:
        # 수신값이 있으면 Rpi 화면에 표시
        # 수신 데이터 마지막에 있는 CR(carriage return) 제거
        b_rcv = ser.readline().rstrip(b'\n\r')
        if b_rcv.startswith(b'\x02') and b_rcv.endswith(b'\x03') and b_rcv != b'':
            b_rcv = b_rcv.lstrip(b'\x02').rstrip(b'\x03')
            s_rcv = b_rcv #.decode('utf-8')
            if s_rcv.lower() == 'x':
                print("Received 'x' from serial port")
                break
            else:
                # print(b_rcv[0], chr(b_rcv[0]))
                print("STX, RTX received: ", b_rcv, s_rcv)
        elif b_rcv == b'':
            continue
        else:
            print("Message not properly sent with STX and ETX : ", b_rcv)

        # Rpi 입력값이 있으면 송신
        # s_snd = input_with_timeout('', 1) # Wait 2 sec to input
        # if s_snd != None:
        #     ser.write((s_snd + '\n').encode('utf-8')) # 송수신은 byte 단위로

except KeyboardInterrupt:
    print("Pressed 'Ctrl+C'")

except (OSError, serial.SerialException):
    print("Check Serial port settings")

else:
    ser.close()

finally:
    print("Bye~")