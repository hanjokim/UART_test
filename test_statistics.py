import statistics


def calculate_stats(data, trim_percent):
    mean = statistics.mean(data)
    minimum = min(data)
    maximum = max(data)
    median = statistics.median(data)

    # 최소값과 최대값을 제외한 데이터로 trimmed mean 계산
    trim_size = int(len(data) * trim_percent / 100)
    trimmed_data = sorted(data)[trim_size:-trim_size]
    trimmed_mean = statistics.mean(trimmed_data)

    return mean, minimum, maximum, median, trimmed_mean


# 예시 데이터
data = [4, 7, 1, 9, 2, 5, 6, 3, 8]
trim_percent = 20

# 통계 계산
result = calculate_stats(data, trim_percent)
print("평균값:", result[0])
print("최소값:", result[1])
print("최대값:", result[2])
print("중간값:", result[3])
print(f"Trimmed mean ({trim_percent}%):", result[4])
