import time
import logging
from functools import wraps
from inspect import iscoroutinefunction

def timer_with_logger(logger=None, log_level=logging.INFO):
    """
    실행 시간을 측정하고 로거에 기록하는 데코레이터
    
    Args:
        logger: 사용할 로거 객체 (None이면 print 사용)
        log_level: 로그 레벨 (기본값: INFO)
    """
    def decorator(func):
        if iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start = time.perf_counter()  
                
                try:
                    result = await func(*args, **kwargs)
                    end = time.perf_counter()
                    execution_time = end - start
                    
                    message = f"⏱️ {func.__name__} 실행 완료 - 소요시간: {execution_time:.4f}초"
                    
                    if logger:
                        logger.log(log_level, message)
                    else:
                        print(message)
                    
                    return result
                    
                except Exception as e:
                    end = time.perf_counter()
                    execution_time = end - start
                    
                    error_message = f"❌ {func.__name__} 실행 실패 - 소요시간: {execution_time:.4f}초, 오류: {str(e)}"
                    
                    if logger:
                        logger.error(error_message)
                    else:
                        print(error_message)
                    
                    raise  # 예외를 다시 발생시켜 호출자가 처리할 수 있도록
                    
            return wrapper
    return decorator
