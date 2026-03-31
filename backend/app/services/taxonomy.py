"""
Taxonomy 버전 관리 서비스 (FR-057).

labeling/taxonomy/ 디렉토리의 YAML 파일을 로드하고,
분류 기준 조회 및 버전 추적 기능을 제공한다.
"""

from pathlib import Path
from typing import Dict, List, Optional

import yaml

from app.core.logging import create_development_logger

logger = create_development_logger(__name__)

# 프로젝트 루트 기준 taxonomy 디렉토리
TAXONOMY_DIR = Path(__file__).resolve().parents[3] / "label_studio" / "taxonomy"

TAXONOMY_FILES = {
    "domain": "domain.yaml",
    "technology": "technology.yaml",
    "company_type": "company_type.yaml",
}


class TaxonomyManager:
    """Taxonomy YAML 파일을 로드하고 분류 기준을 제공하는 관리 클래스."""

    def __init__(self, taxonomy_dir: Optional[Path] = None):
        self._dir = taxonomy_dir or TAXONOMY_DIR
        self._cache: Dict[str, dict] = {}

    # ------------------------------------------------------------------
    # 로드
    # ------------------------------------------------------------------

    def _load(self, name: str) -> dict:
        """YAML 파일 로드 (캐싱)."""
        if name in self._cache:
            return self._cache[name]

        filename = TAXONOMY_FILES.get(name)
        if not filename:
            raise ValueError(f"Unknown taxonomy: {name}")

        path = self._dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Taxonomy file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._cache[name] = data
        return data

    def reload(self) -> None:
        """캐시 초기화 — YAML 변경 후 호출."""
        self._cache.clear()

    # ------------------------------------------------------------------
    # 버전 조회
    # ------------------------------------------------------------------

    def get_version(self, name: str) -> str:
        """특정 taxonomy의 현재 버전을 반환."""
        data = self._load(name)
        return data.get("version", "unknown")

    def get_all_versions(self) -> Dict[str, str]:
        """모든 taxonomy 파일의 버전을 반환."""
        return {name: self.get_version(name) for name in TAXONOMY_FILES}

    # ------------------------------------------------------------------
    # 카테고리 조회
    # ------------------------------------------------------------------

    def get_categories(self, name: str) -> List[str]:
        """분류 카테고리 이름 목록을 반환."""
        data = self._load(name)
        return list(data.get("categories", {}).keys())

    def get_category_detail(self, name: str, category: str) -> Optional[dict]:
        """특정 카테고리의 상세 정보(포함/제외 기준, edge case)를 반환."""
        data = self._load(name)
        return data.get("categories", {}).get(category)

    def get_keywords(self, name: str) -> Dict[str, List[str]]:
        """카테고리별 키워드 사전을 반환."""
        data = self._load(name)
        result = {}
        for cat_name, cat_data in data.get("categories", {}).items():
            result[cat_name] = cat_data.get("keywords", [])
        return result

    # ------------------------------------------------------------------
    # 유효성 검증
    # ------------------------------------------------------------------

    def validate_category(self, name: str, value: str) -> bool:
        """값이 해당 taxonomy의 유효한 카테고리인지 확인."""
        return value in self.get_categories(name)

    def validate_all(self) -> Dict[str, bool]:
        """모든 taxonomy YAML 파일이 정상 로드되는지 확인."""
        results = {}
        for name in TAXONOMY_FILES:
            try:
                self._load(name)
                results[name] = True
            except Exception as e:
                logger.error(f"Taxonomy validation failed for {name}: {e}")
                results[name] = False
        return results


# 싱글톤 인스턴스 — 앱 전역에서 재사용
_manager: Optional[TaxonomyManager] = None


def get_taxonomy_manager() -> TaxonomyManager:
    """TaxonomyManager 싱글톤 인스턴스를 반환."""
    global _manager
    if _manager is None:
        _manager = TaxonomyManager()
    return _manager
