"""
labeling_result CSV + core_tech_result CSV + DB를 합쳐 Label Studio import용 JSON 생성.
도메인 + 기술스택 AI 예측을 pre-annotation으로 포함.
포지션 상세, 주요 업무, 자격요건, 우대사항을 DB에서 직접 로드.
"""

import csv
import html
import json
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

LABELING_DATA_DIR = PROJECT_ROOT / "label_studio" / "imports"
OUTPUT_PATH = Path(__file__).parent / "import_tasks.json"

# 45개 raw 도메인 → 32개 표준 도메인으로 통합
DOMAIN_MAPPING = {
    "블록체인/Web3": "블록체인/웹3",
    "블록체인/핀테크": "금융",
    "여행/레저": "여행/관광",
    "여행/숙박": "여행/관광",
    "국방/안보": "국방/방산",
    "국방/안전": "국방/방산",
    "스포츠/레저": "스포츠",
    "스포츠/피트니스": "스포츠",
    "농업/축산": "농업/식품",
    "해양/수산": "해양/조선",
    "환경/에너지": "에너지",
    "식품/외식": "식품/외식",
}


def standardize_domain(raw_domain: str) -> str:
    return DOMAIN_MAPPING.get(raw_domain, raw_domain)


def format_detail_html(text_val: str) -> str:
    """• 또는 · 기준 줄바꿈 HTML 변환."""
    if not text_val:
        return "<em>내용 없음</em>"
    text_val = html.escape(text_val)
    parts = text_val.split("•")
    if len(parts) > 1:
        text_val = parts[0] + "".join(f"<br>• {p.strip()}" for p in parts[1:])
    parts = text_val.split("·")
    if len(parts) > 1:
        text_val = parts[0] + "".join(f"<br>· {p.strip()}" for p in parts[1:])
    return text_val


def load_posting_texts_from_db() -> dict[str, dict]:
    """DB에서 posting_id별 텍스트 컬럼 로드."""
    from backend.core.database import db_manager, init_database

    if not init_database():
        print("Warning: DB 연결 실패. 텍스트 필드가 비어있을 수 있습니다.")
        return {}

    result = {}
    with db_manager.get_session() as session:
        rows = session.execute(
            text("""
                SELECT posting_id,
                       LEFT(position_detail, 2000),
                       LEFT(main_tasks, 2000),
                       LEFT(requirements, 2000),
                       LEFT(preferred, 2000)
                FROM job_posting
            """)
        ).fetchall()

        for row in rows:
            result[str(row[0])] = {
                "position_detail": row[1] or "",
                "main_tasks": row[2] or "",
                "requirements": row[3] or "",
                "preferred": row[4] or "",
            }
    print(f"Loaded text data for {len(result)} postings from DB")
    return result


def load_core_tech_results() -> dict[str, dict]:
    """core_tech_result.csv에서 posting_id별 기술스택 로드."""
    path = LABELING_DATA_DIR / "core_tech_result.csv"
    if not path.exists():
        print(f"Warning: {path} not found. 기술스택 pre-annotation 없이 진행합니다.")
        return {}

    result = {}
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            posting_id = row["posting_id"].strip()
            techs = json.loads(row["core_technologies"]) if row.get("core_technologies") else []
            tech_cats = json.loads(row["tech_categories"]) if row.get("tech_categories") else []
            result[posting_id] = {
                "techs": techs,
                "tech_categories": tech_cats,
            }
    print(f"Loaded core_tech for {len(result)} postings from CSV")
    return result


def build_tasks() -> list[dict]:
    tasks = []
    seen_posting_ids = set()

    # DB에서 텍스트 로드, CSV에서 기술스택 로드
    posting_texts = load_posting_texts_from_db()
    core_tech_map = load_core_tech_results()

    for i in range(11):
        fname = LABELING_DATA_DIR / f"labeling_result_{i:02d}.csv"
        if not fname.exists():
            print(f"Warning: {fname} not found, skipping")
            continue

        with open(fname, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                posting_id = row["posting_id"].strip()

                if posting_id in seen_posting_ids:
                    continue
                seen_posting_ids.add(posting_id)

                raw_domain = row["domain"].strip()
                std_domain = standardize_domain(raw_domain)

                # 기술스택 정보 (CSV)
                tech_info = core_tech_map.get(posting_id, {})
                techs = tech_info.get("techs", [])
                tech_categories = tech_info.get("tech_categories", [])
                ai_techs_str = ", ".join(techs) if techs else "추출된 기술 없음"

                # 텍스트 정보 (DB)
                texts = posting_texts.get(posting_id, {})
                position_detail = texts.get("position_detail", "") or row.get("position_detail", "")
                main_tasks = texts.get("main_tasks", "")
                requirements = texts.get("requirements", "")
                preferred = texts.get("preferred", "")

                # predictions
                prediction_results = [
                    {
                        "from_name": "domain",
                        "to_name": "position_detail",
                        "type": "choices",
                        "value": {"choices": [std_domain]},
                    }
                ]
                if tech_categories:
                    prediction_results.append({
                        "from_name": "core_technologies",
                        "to_name": "position_detail",
                        "type": "taxonomy",
                        "value": {"taxonomy": tech_categories},
                    })

                task = {
                    "data": {
                        "posting_id": posting_id,
                        "position": row["position"],
                        "position_detail": format_detail_html(position_detail[:2000]),
                        "main_tasks": format_detail_html(main_tasks[:2000]),
                        "requirements": format_detail_html(requirements[:2000]),
                        "preferred": format_detail_html(preferred[:2000]),
                        "ai_domain": std_domain,
                        "ai_techs": ai_techs_str,
                    },
                    "predictions": [
                        {
                            "model_version": "regex-extraction-v1",
                            "result": prediction_results,
                            "score": 0.80,
                        }
                    ],
                }
                tasks.append(task)

    return tasks


if __name__ == "__main__":
    tasks = build_tasks()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
    print(f"\nGenerated {len(tasks)} tasks -> {OUTPUT_PATH}")

    # 통계 출력
    domain_counts = Counter(t["data"]["ai_domain"] for t in tasks)
    print(f"\n도메인 분포 ({len(domain_counts)} categories):")
    for domain, count in domain_counts.most_common():
        print(f"  {domain}: {count}")

    tech_tasks = sum(1 for t in tasks if t["data"]["ai_techs"] != "추출된 기술 없음")
    print(f"\n기술스택 pre-annotation 포함: {tech_tasks}/{len(tasks)}건")
