import statistics


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
    print(len(trimmed_data), trimmed_data, trim_size)
    if trimmed_data == []:
        trimmed_mean = mean
    else:
        trimmed_mean = statistics.mean(trimmed_data)

    return mean, minimum, maximum, median, trimmed_mean


# 예시 데이터
data = [4, 7, 1, 9, 2, 5, 6, 3, 8, 10, 0, 11, 11,11,11, 12,12,12,12,12, 13]
# data = [0,0,0,0,0,0,0,0,0,1,1,2,2]
trim_percent = 20

# 통계 계산
result = calculate_stats(data, trim_percent)
print("평균값:", result[0])
print("최소값:", result[1])
print("최대값:", result[2])
print("중간값:", result[3])
print(f"Trimmed mean ({trim_percent}%):",len(data), result[4])

