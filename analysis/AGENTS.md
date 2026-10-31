# AGENTS.md

<!-- lanternspec:start -->
## 영역 analysis — 이 폴더의 규칙

일하는 방식 · 설계 원칙은 루트 AGENTS.md를 따른다. 아래는 이 폴더에만 해당한다.

### 코드 컨벤션 — Python
- 이 폴더에서 실행하고, 고친 뒤 모두 통과해야 끝: 포맷 `uv run ruff format .` · 린트 `uv run ruff check .` · 타입 검사 `uv run pyright`
- 타입 힌트: 모든 함수의 인자와 반환값 (모양이 정해지지 않은 데이터만 Any)
- 문서 주석 (Google 스타일 docstring · 한국어): 모듈은 책임 한 줄 + 하지 않는 일, 공개 함수 · 클래스는 Google 스타일(Args · Returns · Raises)
<!-- lanternspec:end -->
