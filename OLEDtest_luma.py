from luma.core.interface.serial import i2c, spi, pcf8574
# from luma.core.interface.parallel import bitbang_6800
from luma.core.render import canvas
from luma.oled.device import ssd1306, ssd1309, ssd1325, ssd1331, sh1106, ws0010
from PIL import ImageFont
from time import sleep

# rev.1 users set port=0
# substitute spi(device=0, port=0) below if using that interface
# substitute bitbang_6800(RS=7, E=8, PINS=[25,24,23,27]) below if using that interface
serial = i2c(port=1, address=0x3C)

# substitute ssd1331(...) or sh1106(...) below if using that device
device = ssd1306(serial, rotate=0)
# device = sh1106(serial, rotate=0)

font = ImageFont.truetype('font/pixelmix.ttf', 8)

# Box and text rendered in portrait mode
with canvas(device) as draw:
    draw.rectangle((0, 0, device.width-1, device.height-1), outline="white", fill="black")
    draw.text((0, 0), "1234567890123456789012", font=font, fill="white")
    draw.text((0, 10), "Hello World", font=font, fill="white")
    draw.text((0, 20), "Hello World", font=font, fill="white")
    draw.text((0, 30), "Hello World", font=font, fill="white")
    draw.text((0, 40), "Hello World", font=font, fill="white")
    draw.text((0, 50), "Hello World", font=font, fill="white")
sleep(5)

draw = canvas(device)
draw.rectangle((0, 0, device.width-1, device.height-1), outline="white", fill="black")
draw.text((0, 0), "1234567890123456789012", font=font, fill="white")
draw.text((0, 10), "Hello World", font=font, fill="white")
draw.text((0, 20), "Hello World", font=font, fill="white")
draw.text((0, 30), "Hello World", font=font, fill="white")
draw.text((0, 40), "Hello World", font=font, fill="white")
draw.text((0, 50), "Hello World", font=font, fill="white")
sleep(5)
