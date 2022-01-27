# 파이썬으로 시리얼통신을 위한 가변데이터 만들기
# https://enjoytools.net/xe/board_PZRP31/7897

def addDLE(data):
    # 온리 Data만 DLE 추가. CMD, STX, ETX, chkSUM 모두 안 붙임.
    result = bytes()
    for b in bytearray(data):
        # int to bytes
        # https://stackoverflow.com/questions/21017698/converting-int-to-bytes-in-python-3
        # 데이터 내 아래 조건의 코드 앞에 충돌방지 목적으로 DLE(=FF) 추가
        if b == bytes({b}) == '\x02' or bytes({b}) == b'\x03' or bytes({b}) == b'\x01':
            result = result + b'\xFF' + bytes({b})
        else:
            result = result + bytes({b})
    return result

def getPacketLen(data):
    # 2: 길이(2byte), 1: 체크섬
    len_int = len(packet_pre) + 2 + 1
    result = len_int.to_bytes(2, 'big')  # ARM: Big Endian
    # result = len_int.to_bytes(2, 'little') # Intel: Little Endian
    return bytes(result)

def bXor(b1, b2):  # use xor for bytes
    result = bytearray()
    for b1, b2 in zip(b1, b2):
        result.append(b1 ^ b2)
    return bytes(result)

import codecs

def getChkSum(data):
    ba_data = bytearray(data)
    chksum = bytes()
    for b in range(0, len(data)):
        if b > 0:
            chksum = bXor(bytes(chksum), bytes({ba_data[b]}))
        else:
            chksum = bXor(bytes(b'\x00'), bytes({ba_data[b]}))

        # 결과 확인용
        # print(chksum)
        # print(codecs.encode(chksum, "hex"))
    return chksum

def byteToHex(data):
    result = ''
    for b in bytearray(data):
        result = result + "0x{:02x}".format(b)
        # print(str(hex(b)))
    return result

b_stx = b'\x02'
b_etx = b'\x03'
b_cmd = b'\x01'
b_data = b'\x00\x12\x34\x56\x78\x9a\xbc\xde\xff'

# DLE(Data Link Escape) 추가

b_data = addDLE(b_data)
packet_pre = b_cmd + b_data
packet_len = getPacketLen(packet_pre)

# CheckSum: stx, etx, checksum 제외

chksum = getChkSum(packet_len + packet_pre)
packet_pre = packet_len + packet_pre + chksum + b_etx
packet = b_stx + packet_pre

# print(int.from_bytes(packet_len, byteorder='big')) # 리틀엔디안: Intel / 빅엔디안: ARM

print(packet.hex())

# print((byteToHex(packet)))