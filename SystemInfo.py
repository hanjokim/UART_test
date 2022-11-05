#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2014-2020 Richard Hull and contributors
# See LICENSE.rst for details.
# PYTHON_ARGCOMPLETE_OK

"""
Display system information, current time, and weather.
Tested on 128x128 display (SSD1327).
Needs psutil (+ dependencies) installed::
  $ sudo apt-get install python-dev
  $ sudo -H pip install psutil
"""

import os
import sys
import subprocess
import time
import requests, json
from pathlib import Path
from datetime import datetime

if os.name != 'posix':
    sys.exit('{} platform not supported'.format(os.name))

from demo_opts import get_device
from luma.core.render import canvas
from PIL import ImageFont

try:
    import psutil
except ImportError:
    print("The psutil library was not found. Run 'sudo -H pip install psutil' to install it.")
    sys.exit()

temperature = 0
last_updated = 0
report = None


def bytes2human(n):
    """
    >>> bytes2human(10000)
    '9K'
    >>> bytes2human(100001221)
    '95M'
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = int(float(n) / prefix[s])
            return '%s%s' % (value, s)
    return "%sB" % n


def cpu_usage():
    # load average
    av1, av2, av3 = os.getloadavg()
    return "Ld: %.1f %.1f %.1f" \
           % (av1, av2, av3)


def cpu_uptime():
    # uptime
    uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
    avgString = str(uptime).split(":")[:2]
    return "Up: %s" \
           % (":".join(avgString))


def mem_usage():
    # memory usage
    usage = psutil.virtual_memory()
    return "Mem: %s / %s (%.0f%%)" \
           % (bytes2human(usage.used), bytes2human(usage.total), usage.percent)


def disk_usage(dir):
    # disk usage
    usage = psutil.disk_usage('/')
    return "DU:  %s / %s (%.0f%%)" \
           % (bytes2human(usage.used), bytes2human(usage.total), usage.percent)


def network(iface):
    # network io counters
    stat = psutil.net_io_counters(pernic=True)[iface]
    return "%s: Tx%s, Rx%s" % \
           (iface, bytes2human(stat.bytes_sent), bytes2human(stat.bytes_recv))


def stats(device):
    # use custom font
    font_path = str(Path(__file__).resolve().parent.joinpath('font', 'Hack.ttf'))
    font2 = ImageFont.truetype(font_path, 12)

    # written for 128x128 display, change accordingly
    with canvas(device) as draw:
        draw.text((0, 0), cpu_usage(), font=font2, fill="white")
        draw.text((90, 0), datetime.now().strftime("%H:%M"), font=font2, fill="white")
        draw.text((0, 14), cpu_uptime(), font=font2, fill="white")
        if device.height >= 32:
            draw.text((0, 28), mem_usage(), font=font2, fill="white")

        if device.height >= 64:
            draw.text((0, 42), disk_usage('/'), font=font2, fill="white")
            try:
                draw.text((0, 56), network('eth0'), font=font2, fill="white")
            except KeyError:
                # no wifi enabled/available
                pass

        if device.height >= 76:
            draw.text((0, 70), get_temp(), font=font2, fill="white")

        if device.height >= 88:
            draw.text((0, 84), get_conns(), font=font2, fill="white")

        if device.height >= 100:
            draw.text((0, 106), get_weather(), font=font2, fill="white")


def get_weather():
    # obtain weather description and temperature
    global temperature, report, last_updated
    if last_updated != 0:
        diff = (datetime.now() - last_updated).total_seconds() // 60
    else:
        diff = -1
    # update every 30 mins
    if diff >= 30 or diff == -1:
        BASE_URL = "https://api.openweathermap.org/data/2.5/weather?"
        CITY = "CITY_CODE"
        API_KEY = "API_KEY"
        URL = BASE_URL + "id=" + CITY + "&appid=" + API_KEY
        response = requests.get(URL)
        if response.status_code == 200:
            data = response.json()
            main = data['main']
            temperature = "{:.1f}".format(main['temp'] - 273.15)
            report = data['weather']
            last_updated = datetime.now()
    return "%s°C | %s" % \
           (temperature, report[0]['description'].title())


def get_temp():
    # get cpu temperature
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as temp:
            tmpCel = int(temp.read()[:2])
            tmpPercent = (tmpCel / 55) * 100
    except:
        tmpCel = 0
    finally:
        return "Temp: %s°C" % \
               (str(tmpCel))


def get_conns():
    # get active user sessions
    try:
        # todo: use `psutils` for this
        conns = int(subprocess.check_output('who | wc -l', shell=True))
    except:
        conns = 0
    finally:
        return "Conn: %g" % \
               (conns)


def chop_microseconds(delta):
    # remove microseconds from timedelta
    return delta - datetime.timedelta(microseconds=delta.microseconds)


def main():
    while True:
        stats(device)
        time.sleep(5)


if __name__ == "__main__":
    try:
        device = get_device()
        main()
    except KeyboardInterrupt:
        pass