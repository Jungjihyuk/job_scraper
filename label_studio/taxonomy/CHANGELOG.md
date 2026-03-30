# Taxonomy Changelog

모든 분류 체계 변경사항을 기록합니다.

## [1.0.0] - 2026-03-31

### 초기 버전 수립

**변경 내용:**
- 산업 도메인 분류 체계 신규 수립 (10개 카테고리)
  - 금융/핀테크, 바이오/헬스케어, 커머스/리테일, 게임, 콘텐츠/미디어
  - SaaS/B2B, 교육/에듀테크, 모빌리티/자동차, 보안/사이버보안, AI/딥테크
- 핵심 기술 분류 체계 신규 수립 (10개 카테고리)
  - RAG, LLM, Agent, MLOps, Computer Vision
  - NLP, Data Engineering, Cloud/Infra, Recommendation, Search
- 기업 유형 분류 체계 신규 수립 (7개 카테고리)
  - SI, 대기업IT, 솔루션, IT서비스, 웹에이전시, 스타트업, 미분류
- 각 카테고리별 포함/제외 기준 및 경계 케이스 정의

**사유:**
- FR-057 요구사항: Taxonomy 버전 관리 체계 구축
- 기존 코드 내 하드코딩된 분류 규칙(ContentAnalyzer, CompanyLabeling)을 YAML로 명문화
- 분류 기준 변경 시 영향 범위 추적 가능하도록 버전 관리 도입

**영향 건수:**
- 기존 데이터 영향 없음 (초기 버전, 기존 규칙과 동일)
- 이후 taxonomy_version = "1.0.0"으로 기록되는 모든 신규 분류에 적용
