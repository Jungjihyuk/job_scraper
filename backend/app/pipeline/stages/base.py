import time
import asyncio 
from abc import ABC, abstractmethod
from typing import Any, Set
from app.core.logging import create_development_logger
from app.pipeline.data_models import StageResult

class BaseStage(ABC):
    """🔗 Pipeline Stage 기본 클래스"""
    
    def __init__(self, name: str, enable_duplicate_check: bool = False):
        self.name = name
        self.logger = create_development_logger(f"pipeline.{name}")
        self.enable_duplicate_check = enable_duplicate_check
        self.processed_items: Set[str] = set()
        self.metrics = {
            'items_processed': 0,
            'items_failed': 0,
            'execution_time': 0.0
        }
    
    async def execute(self, data: Any) -> StageResult:
        """🚀 Stage 실행 (메트릭 수집 포함)"""
        start_time = time.time()
        self.logger.info(f"🔄 Starting stage: {self.name}")
        
        try:
            # 실제 처리 로직 실행
            result_data = await self.process(data)
            
            execution_time = int(time.time() - start_time)
            
            # 성공 결과 반환
            stage_result = StageResult(
                stage_name=self.name,
                success=True,
                data=result_data,
                execution_time=execution_time,
                urls_processed=self.metrics['items_processed'],
                urls_failed=self.metrics['items_failed']
            )
            
            self.logger.info(
                f"✅ Stage {self.name} completed: "
                f"{self.metrics['items_processed']} processed, "
                f"{self.metrics['items_failed']} failed, "
                f"{execution_time:.2f}s"
            )
            
            return stage_result
            
        except Exception as e:
            execution_time = int(time.time() - start_time)
            error_msg = f"Stage {self.name} failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            # 실패 결과 반환
            return StageResult(
                stage_name=self.name,
                success=False,
                data=None,
                execution_time=execution_time,
                urls_processed=self.metrics['items_processed'],
                urls_failed=self.metrics['items_failed'],
                error_message=error_msg
            )
    
    @abstractmethod
    async def process(self, data: Any) -> Any:
        """🔧 각 Stage의 핵심 처리 로직 (하위 클래스에서 구현)"""
        pass
    
    def is_duplicate(self, item_id: str) -> bool:
        """🔍 중복 체크"""
        if not self.enable_duplicate_check:
            return False
            
        if item_id in self.processed_items:
            self.logger.debug(f"⚠️ Duplicate item detected: {item_id}")
            return True
            
        self.processed_items.add(item_id)
        return False
    
    def update_metrics(self, processed: int = 0, failed: int = 0):
        """📊 메트릭 업데이트"""
        self.metrics['items_processed'] += processed
        self.metrics['items_failed'] += failed
    
    async def cleanup(self):
        """🧹 Stage 정리 작업 (선택적)"""
        self.logger.debug(f"🧹 Cleaning up stage: {self.name}")
        pass
    
class AsyncBatchStage(BaseStage):
    """⚡ 비동기 배치 처리용 Stage"""
    
    def __init__(self, 
                 name: str, 
                 batch_size: int = 5, 
                 enable_duplicate_check: bool = False):
        super().__init__(name, enable_duplicate_check)
        self.batch_size = batch_size
    
    async def process(self, data: Any) -> Any:
        """배치 단위로 비동기 처리"""
        if not isinstance(data, list):
            data = [data]
        
        results = []
        
        # 배치 단위로 분할 처리
        for i in range(0, len(data), self.batch_size):
            batch = data[i:i + self.batch_size]
            
            self.logger.info(f"🔄 Processing batch {i//self.batch_size + 1}: {len(batch)} items")
            
            # 배치 내 병렬 처리
            tasks = [self.process_single_item(item) for item in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 결과 수집 및 에러 처리
            for item, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    self.logger.error(f"❌ Failed to process item: {item} - {result}")
                    self.update_metrics(failed=1)
                else:
                    results.append(result)
                    self.update_metrics(processed=1)
            
            # 배치 간 딜레이 (선택적)
            if i + self.batch_size < len(data):
                await asyncio.sleep(0.1)
        
        return results
    
    @abstractmethod
    async def process_single_item(self, item: Any) -> Any:
        """🔧 단일 아이템 처리 로직 (하위 클래스에서 구현)"""
        pass