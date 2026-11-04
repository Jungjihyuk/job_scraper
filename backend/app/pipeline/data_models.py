from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

@dataclass
class JobPostingData:
    """URLCollectorStage의 리턴값 
    📎 구직 공고 url 및 포지션/회사/직군 정보
    """
    full_url: str
    position: str
    company: str
    posting_id: str
    job_category: str
    collected_at: datetime = field(default_factory=datetime.now)
    
    def __str__(self):
        return f"{self.position} at {self.company}"


@dataclass  
class ValidatedURL:
    """URLValidatorStage 리턴값
    ✅ 검증된 URL 정보
    """
    job_url: JobPostingData
    is_valid: bool
    status_code: Optional[int] = None
    response_time: Optional[float] = None
    validated_at: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None


@dataclass
class JobDetails:
    """ContentScraperStage 리턴값
    📄 스크래핑된 Job 상세 정보
    """
    job_url: JobPostingData    
    job_description: Dict[str, Any]  # 항목: 내용 ex) 'main_tasks': api 개발. 못 읽은 칸은 None
    posted_date: Optional[datetime] = None
    scraped_at: datetime = field(default_factory=datetime.now)
    scraping_duration: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    location: Optional[str] = None
    location_detail: Optional[str] = None
    experience: Optional[str] = None
    job_field: Optional[str] = None
    normalization_failed: bool = False


@dataclass
class PipelineConfig:
    """⚙️ Pipeline 실행 설정"""
    job: str
    scraper_type: str = "wanted"
    max_scrolls: int = 50
    scroll_delay: int = 2000
    batch_size: int = 5
    request_timeout: int = 10
    enable_duplicate_check: bool = True
    # 수집 모드: "default" (max_scrolls), "incremental" (신규 없으면 조기 종료), "full" (페이지 끝까지)
    scrape_mode: str = "default"
    # 저장 설정
    save_to_database: bool = True
    save_to_local: bool = False
    local_output_format: str = "json"  # json, csv
    local_output_path: str = "logs/"


@dataclass
class StageResult:
    """📊 각 Stage 실행 결과"""
    stage_name: str
    success: bool
    data: Any
    execution_time: float
    urls_processed: int
    urls_failed: int = 0
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PipelineMetrics:
    """📈 Pipeline 전체 성능 메트릭"""
    total_urls_collected: int = 0
    valid_urls: int = 0
    invalid_urls: int = 0
    successful_scrapes: int = 0
    failed_scrapes: int = 0
    saved_count: int = 0  # 실제 저장한 공고 수
    failed_count: int = 0  # 상세 추출 실패 + 저장 실패
    skipped_count: int = 0  # 3회 제한으로 건너뛴 공고 수
    failed_cards: int = 0  # 목록에서 읽지 못한 카드 수
    file_save_failures: int = 0
    batch_status: Optional[str] = None
    total_execution_time: float = 0.0
    stage_results: List[StageResult] = field(default_factory=list)
    
    def add_stage_result(self, result: StageResult):
        """Stage 결과 추가"""
        self.stage_results.append(result)
        self.total_execution_time += result.execution_time
    
    def get_success_rate(self) -> float:
        """성공률 계산"""
        total = self.successful_scrapes + self.failed_scrapes
        return (self.successful_scrapes / total * 100) if total > 0 else 0.0