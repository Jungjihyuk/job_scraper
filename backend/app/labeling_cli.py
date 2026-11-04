"""
CSV 기반 라벨 Import/Export CLI.

Usage:
    # 도메인/기술 라벨링
    uv run app/labeling_cli.py export --output label_studio/cli_pipeline/unlabeled.csv
    uv run app/labeling_cli.py export --all --output label_studio/cli_pipeline/all_postings.csv
    uv run app/labeling_cli.py import --input label_studio/cli_pipeline/labeled.csv --dry-run
    uv run app/labeling_cli.py import --input label_studio/cli_pipeline/labeled.csv

    # 기업 유형 분류
    uv run app/labeling_cli.py company-export --output label_studio/cli_pipeline/companies_unlabeled.csv
    uv run app/labeling_cli.py company-import --input label_studio/cli_pipeline/companies_labeled.csv --dry-run
    uv run app/labeling_cli.py company-import --input label_studio/cli_pipeline/companies_labeled.csv

    # domain_l1 백필 (domain_l2 → domain_l1 자동 매핑)
    uv run app/labeling_cli.py backfill-l1 --dry-run
    uv run app/labeling_cli.py backfill-l1

    # specialty_l1/l2 백필 (기존 공고에 직무 분류 적용)
    uv run app/labeling_cli.py backfill-specialty --dry-run
    uv run app/labeling_cli.py backfill-specialty
    uv run app/labeling_cli.py backfill-specialty --overwrite --limit 100

    # experience_category_id 백필 (경력 텍스트 → ExperienceCategory 연결)
    uv run app/labeling_cli.py backfill-experience --dry-run
    uv run app/labeling_cli.py backfill-experience

    # Taxonomy 기반 재라벨링 (FR-058)
    uv run app/labeling_cli.py relabel --dry-run
    uv run app/labeling_cli.py relabel --target domain
    uv run app/labeling_cli.py relabel --target technology --limit 500
"""

import argparse
import sys

from app.core.database import db_manager
from app.core.logging import create_development_logger
from app.services.labeling import (
    export_postings,
    import_labeled,
    backfill_domain_l1,
    backfill_experience_category,
    backfill_specialty,
    normalize_domain_l2,
)
from app.services.company_labeling import export_companies, import_company_types
from app.services.relabeling import count_relabel_targets, relabel_postings

logger = create_development_logger(__name__)


def cmd_export(args):
    """공고를 CSV로 추출."""
    with db_manager.get_session() as session:
        count = export_postings(
            session=session,
            output_path=args.output,
            field=args.field,
            limit=args.limit,
            include_all=args.all,
        )
    label = "all" if args.all else "unlabeled"
    print(f"Exported {count} {label} postings → {args.output}")


def cmd_import(args):
    """라벨링된 CSV를 DB에 반영."""
    with db_manager.get_session() as session:
        result = import_labeled(
            session=session,
            csv_path=args.input,
            dry_run=args.dry_run,
            skip_existing=args.skip_existing,
        )

    prefix = "[DRY-RUN] " if args.dry_run else ""
    print(
        f"{prefix}Applied: {result['applied']}, "
        f"Skipped: {result['skipped']}, "
        f"Not found: {result['not_found']}, "
        f"Invalid domain: {result['invalid_domain']}"
    )


def cmd_company_export(args):
    """기업을 CSV로 추출."""
    with db_manager.get_session() as session:
        count = export_companies(
            session=session,
            output_path=args.output,
            limit=args.limit,
            include_all=args.all,
        )
    label = "all" if args.all else "unlabeled"
    print(f"Exported {count} {label} companies → {args.output}")


def cmd_company_import(args):
    """기업 유형 CSV를 DB에 반영."""
    with db_manager.get_session() as session:
        result = import_company_types(
            session=session,
            csv_path=args.input,
            dry_run=args.dry_run,
            skip_existing=args.skip_existing,
        )

    prefix = "[DRY-RUN] " if args.dry_run else ""
    print(
        f"{prefix}Applied: {result['applied']}, "
        f"Skipped: {result['skipped']}, "
        f"Not found: {result['not_found']}, "
        f"Invalid type: {result['invalid_type']}"
    )


def cmd_normalize_l2(args):
    """레거시 domain_l2 → 표준 L2로 교정 + L1 채우기."""
    with db_manager.get_session() as session:
        result = normalize_domain_l2(
            session=session,
            dry_run=args.dry_run,
        )

    prefix = "[DRY-RUN] " if args.dry_run else ""
    print(
        f"{prefix}Total legacy: {result['total_legacy']}, "
        f"Normalized: {result['normalized']}"
    )


def cmd_backfill_experience(args):
    """experience 텍스트 → ExperienceCategory 연결 백필."""
    with db_manager.get_session() as session:
        result = backfill_experience_category(
            session=session,
            dry_run=args.dry_run,
            limit=args.limit,
        )

    prefix = "[DRY-RUN] " if args.dry_run else ""
    print(
        f"{prefix}Total target: {result['total_target']}, "
        f"Linked: {result['linked']}, "
        f"No text: {result['no_text']}, "
        f"Failed: {result['failed']}"
    )


def cmd_backfill_specialty(args):
    """기존 공고에 specialty_l1/l2 백필."""
    with db_manager.get_session() as session:
        result = backfill_specialty(
            session=session,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
            limit=args.limit,
        )

    prefix = "[DRY-RUN] " if args.dry_run else ""
    print(
        f"{prefix}Total target: {result['total_target']}, "
        f"Classified: {result['classified']}, "
        f"Unclassified: {result['unclassified']}"
    )


def cmd_backfill_l1(args):
    """domain_l2 → domain_l1 백필."""
    with db_manager.get_session() as session:
        result = backfill_domain_l1(
            session=session,
            dry_run=args.dry_run,
        )

    prefix = "[DRY-RUN] " if args.dry_run else ""
    print(
        f"{prefix}Total missing: {result['total_missing']}, "
        f"Filled: {result['filled']}, "
        f"Invalid L2: {result['invalid']}"
    )


def cmd_relabel(args):
    """Taxonomy 기반 재라벨링."""
    from app.services.taxonomy import get_taxonomy_manager

    mgr = get_taxonomy_manager()
    versions = mgr.get_all_versions()

    print(f"Current taxonomy versions: {versions}")
    print()

    with db_manager.get_session() as session:
        # Step 1: 영향 범위 파악
        counts = count_relabel_targets(session, target=args.target)
        print(f"=== Relabel targets ===")
        for key, val in counts.items():
            print(f"  {key}: {val} postings")
        print()

        if counts.get("total", 0) == 0:
            print("No postings need relabeling. All up to date.")
            return

        # Step 2: 재라벨링 실행
        result = relabel_postings(
            session=session,
            target=args.target,
            dry_run=args.dry_run,
            limit=args.limit,
        )

    prefix = "[DRY-RUN] " if args.dry_run else ""
    print(f"=== {prefix}Relabel results ===")
    print(f"  Total target:   {result.total_target}")
    print(f"  Unchanged:      {result.unchanged}")
    print(f"  Auto-relabeled: {result.auto_relabeled}")
    print(f"  Manual review:  {result.manual_review}")
    print(f"  Errors:         {result.errors}")

    # 변경 상세 출력 (최대 20건)
    if result.changes:
        print()
        print(f"=== Changes detail (showing {min(len(result.changes), 20)}"
              f"/{len(result.changes)}) ===")
        for change in result.changes[:20]:
            action_icon = (
                "🔄" if change["action"] == "auto_relabel" else "⚠️"
            )
            print(
                f"  {action_icon} {change['posting_id']}: "
                f"{change['field']} "
                f"'{change['old']}' → '{change['new']}' "
                f"(confidence: {change['confidence']:.2f})"
            )


def main():
    parser = argparse.ArgumentParser(
        description="CSV 기반 라벨 Import/Export 파이프라인"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # export
    export_parser = subparsers.add_parser("export", help="공고 CSV 추출")
    export_parser.add_argument(
        "--output", "-o", default="label_studio/cli_pipeline/unlabeled.csv", help="출력 CSV 경로"
    )
    export_parser.add_argument(
        "--field",
        choices=["domain", "technology"],
        default=None,
        help="필터 대상 (domain만 / technology만 / 생략시 둘 다)",
    )
    export_parser.add_argument(
        "--limit", "-l", type=int, default=None, help="최대 추출 건수"
    )
    export_parser.add_argument(
        "--all",
        action="store_true",
        help="이미 라벨링된 공고도 포함하여 전체 추출",
    )

    # import
    import_parser = subparsers.add_parser("import", help="라벨링 CSV DB 반영")
    import_parser.add_argument(
        "--input", "-i", required=True, help="입력 CSV 경로"
    )
    import_parser.add_argument(
        "--dry-run", action="store_true", help="실제 반영 없이 결과만 확인"
    )
    import_parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="이미 값이 있는 필드는 건너뜀",
    )

    # company-export
    ce_parser = subparsers.add_parser(
        "company-export", help="기업 유형 분류용 CSV 추출"
    )
    ce_parser.add_argument(
        "--output",
        "-o",
        default="label_studio/cli_pipeline/companies_unlabeled.csv",
        help="출력 CSV 경로",
    )
    ce_parser.add_argument(
        "--limit", "-l", type=int, default=None, help="최대 추출 건수"
    )
    ce_parser.add_argument(
        "--all",
        action="store_true",
        help="이미 분류된 기업도 포함하여 전체 추출",
    )

    # company-import
    ci_parser = subparsers.add_parser(
        "company-import", help="기업 유형 CSV DB 반영"
    )
    ci_parser.add_argument(
        "--input", "-i", required=True, help="입력 CSV 경로"
    )
    ci_parser.add_argument(
        "--dry-run", action="store_true", help="실제 반영 없이 결과만 확인"
    )
    ci_parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="이미 분류된 기업은 건너뜀",
    )

    # normalize-l2
    nl_parser = subparsers.add_parser(
        "normalize-l2",
        help="레거시 domain_l2를 표준 L2로 교정 + L1 채우기",
    )
    nl_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 변경 없이 대상 건수만 확인",
    )

    # backfill-experience
    be_parser = subparsers.add_parser(
        "backfill-experience",
        help="experience 텍스트 → ExperienceCategory 연결 백필",
    )
    be_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 변경 없이 대상 건수만 확인",
    )
    be_parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="처리할 최대 건수",
    )

    # backfill-specialty
    bs_parser = subparsers.add_parser(
        "backfill-specialty",
        help="기존 공고에 specialty_l1/l2 백필 (키워드 기반 직무 분류)",
    )
    bs_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 변경 없이 대상 건수만 확인",
    )
    bs_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="이미 값이 있는 레코드도 재분류",
    )
    bs_parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="처리할 최대 건수",
    )

    # backfill-l1
    bf_parser = subparsers.add_parser(
        "backfill-l1",
        help="domain_l2는 있지만 domain_l1이 비어있는 레코드 백필",
    )
    bf_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 변경 없이 대상 건수만 확인",
    )

    # relabel (FR-058)
    relabel_parser = subparsers.add_parser(
        "relabel", help="Taxonomy 기반 재라벨링"
    )
    relabel_parser.add_argument(
        "--target",
        choices=["domain", "technology"],
        default=None,
        help="재라벨링 대상 (생략 시 전체)",
    )
    relabel_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 변경 없이 영향 범위만 확인",
    )
    relabel_parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="처리할 최대 건수",
    )

    args = parser.parse_args()

    # DB 초기화
    if not db_manager.initialize():
        logger.error("Failed to initialize database")
        sys.exit(1)

    try:
        if args.command == "export":
            cmd_export(args)
        elif args.command == "import":
            cmd_import(args)
        elif args.command == "company-export":
            cmd_company_export(args)
        elif args.command == "company-import":
            cmd_company_import(args)
        elif args.command == "normalize-l2":
            cmd_normalize_l2(args)
        elif args.command == "backfill-experience":
            cmd_backfill_experience(args)
        elif args.command == "backfill-specialty":
            cmd_backfill_specialty(args)
        elif args.command == "backfill-l1":
            cmd_backfill_l1(args)
        elif args.command == "relabel":
            cmd_relabel(args)
    finally:
        db_manager.close()


if __name__ == "__main__":
    main()
