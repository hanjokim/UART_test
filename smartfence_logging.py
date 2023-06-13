# -*- coding: utf-8 -*-
'''
1. 수집 날짜 및 시간정보 (ex. 2023/03/20 17:09:43) (10초 간격으로 데이터 수집)
2. PM1.0 (ex. 27)
3. PM2.5 (ex. 39)
4. PM10 (ex. 44)
5. PM 1.0 1분간 average (ex. 25, 35, 45)
6. PM 2.5 1분간 average (ex. 25, 35, 45)
7. PM 10 1분간 average (ex. 25, 35, 45)
8. PM 1.0 1분간 min (ex. 22, 31, 41)
9. PM 2.5 1분간 min (ex. 22, 31, 41)
10. PM 10 1분간 min (ex. 22, 31, 41)
11. PM 1.0 1분간 max (ex. 28, 39, 48)
12. PM 2.5 1분간 max (ex. 28, 39, 48)
13. PM 10 1분간 max (ex. 28, 39, 48)
14. PM 1.0 1분간 median (ex. 25, 34, 44)
15. PM 2.5 1분간 median (ex. 25, 34, 44)
16. PM 10 1분간 median (ex. 25, 34, 44)
17. PM 1.0 1분간 trimmed mean (ex. 25, 35, 45)
18. PM 2.5 1분간 trimmed mean (ex. 25, 35, 45)
19. PM 10 1분간 trimmed mean (ex. 25, 35, 45)
20. 온도 (ex. 19.3)
21. 습도 (ex. 15.3)
22. 위도
23. 경도
24. PM 센서 상태 "OK" / "NG"
25. GPS 센서 상태 "FX" / "NF" Fixed / Not Fixed
26. 현재 팬 동작 상태 (대기, 자동(1, 2, 3, 4, 5단), 수동(1, 2, 3, 4, 5단)) 'W' / 'A' / 'M'
27. 장치 오류 알림 "OK" / "NG"
28. Checksum
'''
import os

# import requests
# import signal

import configparser
import sys
import serial
import time
import threading
import struct
import statistics
from datetime import datetime
from datetime import timedelta
# import logging
import logging.handlers

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306,  sh1106

# from PIL import Image
# from PIL import ImageDraw
from PIL import ImageFont

conf_values = configparser.ConfigParser()
conf_values.read('config_smartfence.ini')
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
log_mode = general['log_mode']
log_interval = general.getint('log_interval')
average_window = general.getint('average_window')
sample_no = int(average_window / update_interval)
trim_percent = general.getint('trim_percent')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')


if log_mode == 'midnight':
    log_interval = 1

timedfilehandler = logging.handlers.TimedRotatingFileHandler(filename='log/smartfencelog', when=log_mode, interval=log_interval, encoding='utf-8', utc=False)
# timedfilehandler.setFormatter(formatter)
timedfilehandler.suffix = "%Y%m%d"
# timedfilehandler.suffix = "%Y%m%d_%H%M%S"

logger.addHandler(timedfilehandler)
meas_data = {
    "pm1": 0,
    "pm25": 0,
    "pm10": 0,
    "temp": None,
    "humi": None,
    "long": None,
    "lati": None,
    "pm1_average": 0,
    "pm25_average": 0,
    "pm10_average": 0,
    "pm1_min": 0,
    "pm25_min": 0,
    "pm10_min": 0,
    "pm1_max": 0,
    "pm25_max": 0,
    "pm10_max": 0,
    "pm1_median": 0,
    "pm25_median": 0,
    "pm10_median": 0,
    "pm1_tmean": 0,
    "pm25_tmean": 0,
    "pm10_tmean": 0,
    "timestamp": "",
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
        print("OLED driver configuration error in config_smartfence.ini")
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


def get_fan_status():
    fan_status = "W"
    return fan_status


def get_device_status():
    device_status = "OK"
    return device_status


def calculate_stats(data, trim_percent):
    temp = [num for num in data if num > 0]
    if temp == []:
        return 0, 0, 0, 0, 0
    mean = statistics.mean(temp)
    minimum = min(temp)
    maximum = max(temp)
    median = statistics.median(temp)

    # 상하위 20%를 제외한 데이터로 trimmed mean 계산
    trim_size = int(len(temp) * trim_percent / 2 / 100)
    trimmed_data = sorted(temp)[trim_size:-trim_size]
    if trimmed_data == []:
        trimmed_mean = mean
    else:
        trimmed_mean = statistics.mean(trimmed_data)

    return mean, minimum, maximum, median, trimmed_mean


def parsing_pm_data(packed_data):
    tmp = struct.unpack('!16h', packed_data)
    # print(f'PM input data : {tmp}')
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
    else:
        return -1


def parsing_gps_data(gps_bytes):
    try:
        string = gps_bytes.decode('utf-8')
        gps_data = string.rstrip().split(',')
        if check_gps_data(gps_data) == 1:
            # print(f'GPS input data : {gps_data}')
            return gps_data
        else:
            return -1
    except UnicodeDecodeError:
        return -1


# 데이터 체크 함수
def check_gps_data(data):
    if '$GPRMC' in data or '$GNRMC' in data:
        return 1
    else:
        return -1


def calculate_checksum(data):
    """
    문자열과 정수, 부동 소수점으로 구성된 리스트의 체크섬을 계산합니다.
    :param data: 문자열과 숫자로 이루어진 리스트
    :return: 체크섬 값 (16진수 문자열)
    """
    checksum = 0

    for item in data:
        if isinstance(item, str):
            item = item.encode()  # 문자열을 바이트로 변환

        checksum += hash(item)
        checksum &= 0xFFFF  # 16비트로 제한

    return format(checksum, '04X')  # 16진수 문자열로 반환

# 본 쓰레드
def readThread(pm_ser, gps_ser):
    # global line
    global exitThread
    global clock_set
    global pm_err_count
    # global pm_status
    # global gps_status
    global sample_no
    global trim_percent

    # 쓰레드 종료될때까지 계속 돌림
    while not exitThread:
        meas_data["timestamp"] = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        temp = pm_ser.readline(pm_data_size)

        if len(temp) == pm_data_size:
            pm_data = parsing_pm_data(temp)
            if pm_data != -1:
                # pm_status = "OK"
                meas_data["pm1"] = pm_data[2]
                meas_data["pm25"] = pm_data[3]
                meas_data["pm10"] = pm_data[4]
                meas_data["temp"] = (pm_data[12] / 10.) if is_PMS7003T else None
                meas_data["humi"] = (pm_data[13] / 10.) if is_PMS7003T else None
            else:
                # pm_status = "NG"
                meas_data["pm1"] = 0
                meas_data["pm25"] = 0
                meas_data["pm10"] = 0
                meas_data["temp"] = None
                meas_data["humi"] = None
        else:
            pm_ser.reset_input_buffer()

        temp = gps_ser.readline()
        gps_data = parsing_gps_data(temp)

        if gps_data != -1 and len(gps_data) >= 3:
            if (gps_data[0] == "$GPRMC" or gps_data[0] == "$GNRMC") and gps_data[2] == 'A':
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

        time.sleep(thread_interval)


if __name__ == "__main__":
    # 시리얼 열기
    pm_ser = serial.Serial(pm_port, pm_baud, timeout=pm_timeout)
    gps_ser = serial.Serial(gps_port, gps_baud, timeout=gps_timeout)

    # 시리얼 읽을 쓰레드 생성
    thread = threading.Thread(target=readThread, args=(pm_ser, gps_ser, ))

    # 시작!
    thread.start()

    fan_status = "W"
    device_status = "NG"
    pm_status = "NG"
    gps_status = "NF"
    checksum = 0

    # list for average sampling data
    stat_cycle = 0
    sample_pm1 = []
    sample_pm25 = []
    sample_pm10 = []
    stats_pm1 = []
    stats_pm25 = []
    stats_pm10 = []

    try:
        while True:
            stat_cycle += 1

            if None in [meas_data["pm1"], meas_data["pm25"], meas_data["pm10"], meas_data["temp"], meas_data["humi"]]:
                pm_status = "NG"
            else:
                pm_status = "OK"

            if None in [meas_data["long"], meas_data["lati"]]:
                gps_status = "NF"
            else:
                gps_status = "FX"

            # dtstring = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
            dtstring = meas_data['timestamp']

            fan_status = get_fan_status()
            device_status = get_device_status()

            sample_pm1.append(meas_data["pm1"])
            sample_pm25.append(meas_data["pm25"])
            sample_pm10.append(meas_data["pm10"])

            if stat_cycle == sample_no:
                meas_data["pm1_average"], meas_data["pm1_min"], meas_data["pm1_max"], meas_data["pm1_median"], meas_data["pm1_tmean"] = calculate_stats(sample_pm1, trim_percent)
                meas_data["pm25_average"], meas_data["pm25_min"], meas_data["pm25_max"], meas_data["pm25_median"], meas_data["pm25_tmean"] = calculate_stats(sample_pm25, trim_percent)
                meas_data["pm10_average"], meas_data["pm10_min"], meas_data["pm10_max"], meas_data["pm10_median"], meas_data["pm10_tmean"] = calculate_stats(sample_pm10, trim_percent)
                sample_pm1 = []
                sample_pm25 = []
                sample_pm10 = []
                stat_cycle = 0

            checksum = calculate_checksum(list(meas_data.values()))

            logger.info(f'{dtstring},{meas_data["pm1"]},{meas_data["pm25"]},{meas_data["pm10"]},'
                        f'{meas_data["pm1_average"]:.1f},{meas_data["pm25_average"]:.1f},{meas_data["pm10_average"]:.1f},'
                        f'{meas_data["pm1_min"]},{meas_data["pm25_min"]},{meas_data["pm10_min"]},'
                        f'{meas_data["pm1_max"]},{meas_data["pm25_max"]},{meas_data["pm10_max"]},'
                        f'{meas_data["pm1_median"]},{meas_data["pm25_median"]},{meas_data["pm10_median"]},'
                        f'{meas_data["pm1_tmean"]:.1f},{meas_data["pm25_tmean"]:.1f},{meas_data["pm10_tmean"]:.1f},'
                        f'{meas_data["temp"]},{meas_data["humi"]},{meas_data["long"]},{meas_data["lati"]},'
                        f'{pm_status},{gps_status},{fan_status},{device_status},{checksum}')

            print(f'Logged OK - {dtstring},{meas_data["pm1"]},{meas_data["pm25"]},{meas_data["pm10"]},'
                        f'{meas_data["pm1_average"]:.1f},{meas_data["pm25_average"]:.1f},{meas_data["pm10_average"]:.1f},'
                        f'{meas_data["pm1_min"]},{meas_data["pm25_min"]},{meas_data["pm10_min"]},'
                        f'{meas_data["pm1_max"]},{meas_data["pm25_max"]},{meas_data["pm10_max"]},'
                        f'{meas_data["pm1_median"]},{meas_data["pm25_median"]},{meas_data["pm10_median"]},'
                        f'{meas_data["pm1_tmean"]:.1f},{meas_data["pm25_tmean"]:.1f},{meas_data["pm10_tmean"]:.1f},'
                        f'{meas_data["temp"]},{meas_data["humi"]},{meas_data["long"]},{meas_data["lati"]},'
                        f'{pm_status},{gps_status},{fan_status},{device_status},{checksum}')
            # logger.info("%s,%.1f,%.1f,%.1f,%.1f,%.1f,%.5f,%.5f",
            #             dtstring,
            #             meas_data["pm1"], meas_data["pm25"], meas_data["pm10"], meas_data["temp"], meas_data["humi"],
            #             meas_data["long"], meas_data["lati"])
            # print("Logged OK- %s" % meas_data, f'{pm_status=},{gps_status=},{fan_status=},{device_status=},{checksum=}')

            # _dt = datetime.fromtimestamp(int(meas_data["timestamp"])).strftime('%Y-%m-%d %H:%M:%S')

            disp_OLED(meas_data)

            meas_data["pm1"] =  0
            meas_data["pm25"] = 0
            meas_data["pm10"] = 0
            meas_data["temp"] = None
            meas_data["humi"] = None
            meas_data["long"] = None
            meas_data["lati"] = None
            meas_data["timestamp"] = None

            time.sleep(update_interval)
    except KeyboardInterrupt:
        print("Stop Measuring...")
        exitThread = 1
        device.hide()
        pm_ser.close()
        gps_ser.close()
        sys.exit()
