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


# 예시 데이터
data = ['hello', 42, 3.14, 'world']

# 체크섬 계산
checksum = calculate_checksum(data)
print("Checksum:", checksum)
