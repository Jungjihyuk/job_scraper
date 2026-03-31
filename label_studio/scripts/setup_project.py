"""
Label Studio 프로젝트 생성 + 태스크 import 스크립트.
Label Studio가 실행 중인 상태에서 실행해야 함.

사용법:
    # 1. 먼저 import_tasks.json 생성
    python label_studio/scripts/prepare_import_data.py

    # 2. 프로젝트 생성 + import
    python label_studio/scripts/setup_project.py
"""

import json
import sys
from pathlib import Path

import requests

from auth import get_auth_headers, LS_URL

SCRIPT_DIR = Path(__file__).parent
IMPORT_FILE = SCRIPT_DIR / "import_tasks.json"
CONFIG_FILE = SCRIPT_DIR / "labeling_config.xml"


def check_prerequisites():
    if not IMPORT_FILE.exists():
        print(f"Error: {IMPORT_FILE} 파일이 없습니다.")
        print("  먼저 실행: uv run label_studio/scripts/prepare_import_data.py")
        sys.exit(1)

    # Label Studio 연결 확인
    try:
        resp = requests.get(f"{LS_URL}/api/health", timeout=5)
        if resp.status_code != 200:
            print(f"Error: Label Studio가 응답하지 않습니다 ({LS_URL})")
            sys.exit(1)
    except requests.ConnectionError:
        print(f"Error: Label Studio에 연결할 수 없습니다 ({LS_URL})")
        print("  docker compose up -d label-studio 로 먼저 실행하세요.")
        sys.exit(1)


def create_project() -> int:
    headers = get_auth_headers()

    with open(CONFIG_FILE, encoding="utf-8") as f:
        label_config = f.read()

    payload = {
        "title": "채용공고 도메인 + 기술스택 검수",
        "description": "AI 예측 결과 검수: 산업 도메인 분류 + 핵심 기술 스택 태깅",
        "label_config": label_config,
        "expert_instruction": (
            "1. 도메인: AI가 예측한 도메인을 확인하고 올바른 도메인을 선택하세요.\n"
            "2. 기술스택: AI가 추출한 기술 목록을 확인하고 Taxonomy에서 수정하세요.\n"
            "   - 잘못 추출된 기술은 제거, 누락된 기술은 추가하세요.\n"
            "   - position_detail 내용을 참고하여 판단하세요.\n"
            "3. 판단이 어려운 도메인은 '미분류'를 선택하세요."
        ),
        "show_instruction": True,
        "show_skip_button": True,
        "enable_empty_annotation": False,
    }

    resp = requests.post(
        f"{LS_URL}/api/projects",
        json=payload,
        headers=headers,
    )

    if resp.status_code == 201:
        project_id = resp.json()["id"]
        print(f"Project created: id={project_id}")
        return project_id
    else:
        print(f"Error creating project: {resp.status_code}")
        print(resp.text)
        sys.exit(1)


def import_tasks(project_id: int):
    headers = get_auth_headers()

    with open(IMPORT_FILE, encoding="utf-8") as f:
        tasks = json.load(f)

    print(f"Importing {len(tasks)} tasks...")

    BATCH_SIZE = 100
    total_imported = 0

    for i in range(0, len(tasks), BATCH_SIZE):
        batch = tasks[i : i + BATCH_SIZE]
        resp = requests.post(
            f"{LS_URL}/api/projects/{project_id}/import",
            json=batch,
            headers=headers,
        )

        if resp.status_code == 201:
            count = resp.json().get("task_count", len(batch))
            total_imported += count
            print(f"  Batch {i//BATCH_SIZE + 1}: {count} tasks imported")
        else:
            print(f"  Error at batch {i}: {resp.status_code} {resp.text[:200]}")

    print(f"\nTotal imported: {total_imported} tasks")
    return total_imported


def verify_project(project_id: int):
    headers = get_auth_headers()
    resp = requests.get(f"{LS_URL}/api/projects/{project_id}", headers=headers)

    if resp.status_code == 200:
        info = resp.json()
        print(f"\nProject verification:")
        print(f"  Title: {info['title']}")
        print(f"  Tasks: {info['task_number']}")
        print(f"  Annotations: {info['num_tasks_with_annotations']}")
        print(f"\nLabel Studio URL: {LS_URL}/projects/{project_id}")
    else:
        print(f"Error verifying project: {resp.status_code}")


if __name__ == "__main__":
    check_prerequisites()
    project_id = create_project()
    import_tasks(project_id)
    verify_project(project_id)
