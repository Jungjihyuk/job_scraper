import json
import csv
import os
from datetime import datetime
from typing import List
from pathlib import Path

from job_scraper.pipeline.core.base_stage import BaseStage
from job_scraper.pipeline.core.data_models import JobDetails, PipelineConfig


class LocalFileSaverStage(BaseStage):
    """📁 로컬 파일 저장 Stage - JSON/CSV 형식으로 로컬에 저장"""
    
    def __init__(self):
        super().__init__("LocalFileSaver")
        
    async def process(self, data: tuple) -> List[JobDetails]:
        """로컬 파일로 저장 후 원본 데이터 반환"""
        job_details_list, config = data
        
        if not config.save_to_local:
            self.logger.info("🚫 로컬 저장이 비활성화됨")
            return job_details_list
            
        if not job_details_list:
            self.logger.info("📝 저장할 데이터가 없음")
            return job_details_list
            
        try:
            # 출력 디렉터리 생성
            output_dir = Path(config.local_output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 파일명 생성 (타임스탬프 포함)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"job_scraping_{config.job}_{timestamp}"
            
            if config.local_output_format.lower() == "json":
                await self._save_as_json(job_details_list, output_dir, filename)
            elif config.local_output_format.lower() == "csv":
                await self._save_as_csv(job_details_list, output_dir, filename)
            else:
                self.logger.warning(f"⚠️ 지원하지 않는 형식: {config.local_output_format}")
                
            self.update_metrics(processed=len(job_details_list))
            self.logger.info(f"✅ {len(job_details_list)}개 항목을 로컬에 저장 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 로컬 저장 실패: {e}")
            self.update_metrics(failed=len(job_details_list))
            
        return job_details_list
    
    async def _save_as_json(self, job_details_list: List[JobDetails], output_dir: Path, filename: str):
        """JSON 형식으로 저장"""
        file_path = output_dir / f"{filename}.json"
        
        # JobDetails 객체를 딕셔너리로 변환
        data_to_save = []
        for job in job_details_list:
            job_dict = {
                "url": job.job_url.full_url,
                "position": job.job_url.position,
                "company": job.job_url.company,
                "job_category": job.job_url.job_category,
                "posting_id": job.job_url.posting_id,
                "success": job.success,
                "scraped_at": job.scraped_at.isoformat() if job.scraped_at else None,
                "scraping_duration": job.scraping_duration,
                "location": job.location,
                "experience": job.experience,
                "job_field": job.job_field,
                "job_description": job.job_description,
                "error_message": job.error_message
            }
            data_to_save.append(job_dict)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            
        self.logger.info(f"💾 JSON 파일 저장: {file_path}")
    
    async def _save_as_csv(self, job_details_list: List[JobDetails], output_dir: Path, filename: str):
        """CSV 형식으로 저장"""
        file_path = output_dir / f"{filename}.csv"
        
        fieldnames = [
            'url', 'position', 'company', 'job_category', 'posting_id',
            'success', 'scraped_at', 'scraping_duration', 'location', 
            'experience', 'job_field', 'error_message'
        ]
        
        # job_description 필드들 추가
        all_desc_keys = set()
        for job in job_details_list:
            if job.job_description:
                all_desc_keys.update(job.job_description.keys())
        
        desc_fields = [f"job_desc_{key}" for key in sorted(all_desc_keys)]
        fieldnames.extend(desc_fields)
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for job in job_details_list:
                row = {
                    'url': job.job_url.full_url,
                    'position': job.job_url.position,
                    'company': job.job_url.company,
                    'job_category': job.job_url.job_category,
                    'posting_id': job.job_url.posting_id,
                    'success': job.success,
                    'scraped_at': job.scraped_at.isoformat() if job.scraped_at else '',
                    'scraping_duration': job.scraping_duration or '',
                    'location': job.location or '',
                    'experience': job.experience or '',
                    'job_field': job.job_field or '',
                    'error_message': job.error_message or ''
                }
                
                # job_description 필드들 추가
                if job.job_description:
                    for key, value in job.job_description.items():
                        row[f"job_desc_{key}"] = value
                
                writer.writerow(row)
                
        self.logger.info(f"💾 CSV 파일 저장: {file_path}")