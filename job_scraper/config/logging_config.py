import os
import logging

def setup_logger(name):
    """
    모듈별 로깅 설정을 위한 함수.
    각 모듈의 __name__을 받아 해당 모듈 전용 로거를 생성.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # 필요에 따라 로그 레벨 조정

    # 로그 파일 경로 설정 (모듈명 기반)
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)  # logs 폴더 없으면 생성
    log_file = os.path.join("..",log_dir, f"{name}.log")  # 파일명 자동 설정

    # 파일 핸들러 설정
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # 로그 포맷 설정
    formatter = logging.Formatter(
        "%(asctime)s - [%(levelname)s] - %(filename)s - %(funcName)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # 콘솔 출력 핸들러 추가
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # 콘솔에서는 INFO 이상만 출력
    console_handler.setFormatter(formatter)

    # 핸들러 등록
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
