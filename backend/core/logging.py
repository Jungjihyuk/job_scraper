import os
import logging
from typing import Optional

def setup_logger(
    name: str, 
    log_level: str = "INFO",
    file_level: Optional[str] = None,
    console_level: Optional[str] = None,
    enable_console: bool = True,
    enable_file: bool = True
):
    """
    모듈별 로깅 설정을 위한 개선된 함수.
    
    Args:
        name: 로거 이름 (보통 모듈명)
        log_level: 기본 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        file_level: 파일 출력 레벨 (None이면 log_level 사용)
        console_level: 콘솔 출력 레벨 (None이면 log_level 사용)
        enable_console: 콘솔 출력 활성화 여부
        enable_file: 파일 출력 활성화 여부
    
    Returns:
        logging.Logger: 설정된 로거 객체
    """
    
    # 1. 로거 생성 (이미 존재하면 기존 로거 반환)
    logger = logging.getLogger(name)
    
    # 2. 중복 핸들러 방지 - 기존 핸들러가 있으면 제거
    if logger.handlers:
        logger.handlers.clear()
    
    # 3. 로그 레벨 설정
    log_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO, 
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    # 기본 로거 레벨 설정
    logger.setLevel(log_levels.get(log_level.upper(), logging.INFO))
    
    # 4. 로그 포맷 설정
    detailed_formatter = logging.Formatter(
        "%(asctime)s - [%(levelname)8s] - %(name)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    simple_formatter = logging.Formatter(
        "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
        datefmt="%H:%M:%S"
    )
    
    # 5. 파일 핸들러 설정
    if enable_file:
        # 로그 디렉토리 생성
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # 파일 경로 설정 (프로젝트 루트 기준)
        log_file = os.path.join(log_dir, f"{name}.log")
        
        # 파일 핸들러 생성
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_level_setting = file_level or log_level
        file_handler.setLevel(log_levels.get(file_level_setting.upper(), logging.INFO))
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    # 6. 콘솔 핸들러 설정
    if enable_console:
        console_handler = logging.StreamHandler()
        console_level_setting = console_level or log_level
        console_handler.setLevel(log_levels.get(console_level_setting.upper(), logging.INFO))
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
    
    # 7. 상위 로거로의 전파 방지 (중복 출력 방지)
    logger.propagate = False
    
    return logger


def create_debug_logger(name: str):
    """모든 레벨의 로그를 보고 싶을 때 사용"""
    return setup_logger(
        name=name,
        log_level="DEBUG",
        file_level="DEBUG", 
        console_level="DEBUG"
    )
    
def create_development_logger(name: str):
    """개발 환경용 로거"""
    return setup_logger(
        name=name,
        log_level="DEBUG",
        file_level="DEBUG",
        console_level="INFO"
    )
    