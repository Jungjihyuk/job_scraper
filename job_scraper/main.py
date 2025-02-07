import argparse
import sys
import time

import inquirer

from job_scraper.config.logging_config import setup_logger
from job_scraper.scrapers.scraper_manager import ScraperManager
from job_scraper.scrapers.wanted_scraper import WantedScraper

logger = setup_logger(__name__)

questions = [
    inquirer.Checkbox(
        "job",
        message="원하는 직무를 선택하시려면 스페이스바로 체크 후 엔터를 눌러주세요.",
        choices=[
            "파이썬 개발자",
            "머신러닝 엔지니어",
            "데이터 엔지니어",
            "DBA",
            "서버 개발자",
            "빅데이터 엔지니어",
            ".NET 개발자",
        ],
    )
]
answers = inquirer.prompt(questions)
if answers is None:
    sys.exit(1)


async def main(opt):
    logger.info(f"Start main function (job: {opt.job[0]})")
    manager = ScraperManager(scraper_classes=[WantedScraper], jobs=[opt.job[0]])
    await manager.run()


def parse_opt(known=False):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--job", type=list, default=answers["job"], help="Choose the job"
    )

    return parser.parse_known_args()[0] if known else parser.parse_args()


if __name__ == "__main__":
    start = time.time()
    opt = parse_opt()

    import asyncio

    asyncio.run(main(opt))
    logger.info("Finish the work: {0:.2f} sec".format(time.time() - start))
