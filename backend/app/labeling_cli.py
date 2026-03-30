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
"""

import argparse
import sys

from app.core.database import db_manager
from app.core.logging import create_development_logger
from app.services.labeling import export_postings, import_labeled
from app.services.company_labeling import export_companies, import_company_types

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
    finally:
        db_manager.close()


if __name__ == "__main__":
    main()
