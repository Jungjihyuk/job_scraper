# Query parameter 
JOB_CONFIG = {
    "job_id": {
        "파이썬 개발자": 899,
        "머신러닝 엔지니어": 1634,
        "데이터 엔지니어": 655,
        "DBA": 10231,
        "서버 개발자": 872,
        "빅데이터 엔지니어": 1025,
        ".NET 개발자": 661
    },
    "params": {
        "country": "kr",
        "job_sort": "job.recommend_order",
        "years": -1,
        "locations": "gyeonggi.all",
    },
}

# 공통 헤더 정보
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
}

# User-Agent 리스트
USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4; en-US) AppleWebKit/533.19 (KHTML, like Gecko) Chrome/55.0.3576.124 Safari/536",
    "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 7_7_1) AppleWebKit/603.19 (KHTML, like Gecko) Chrome/52.0.1487.224 Safari/601",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.3; x64) AppleWebKit/600.6 (KHTML, like Gecko) Chrome/48.0.1678.303 Safari/536",
    "Mozilla/5.0 (Windows; U; Windows NT 6.0;; en-US) AppleWebKit/600.48 (KHTML, like Gecko) Chrome/51.0.1349.219 Safari/537",
    "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 8_5_9; en-US) Gecko/20100101 Firefox/46.3",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_2_2) Gecko/20100101 Firefox/60.1"
]
