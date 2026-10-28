---
name: l-learn
description: 모르는 기술을 내 지식 저장소와 비교 — 기술 용어를 지식 저장소(Obsidian)에서 찾아 🟢 노트 있음 · 🟡 노트 있는데 다시 물음 · 🔴 노트 없음으로 나누고, 이해 부채 카드(📒 부채/카드/D-NNN)를 만들거나 물은 횟수를 늘리고, 복습할 것과 새로 공부할 것(학습 노트 초안)을 제안한다. Use when the user asks what a technology is, or when /l-plan · /l-design · /l-build hand over unfamiliar terms.
---
<!-- lanternspec가 생성한 파일 — 원본: lanternspec/resources/skills. `lantern upgrade`가 다시 만든다 (직접 고치면 upgrade가 건너뜀) -->

# /l-learn — 모르는 기술을 지식 저장소와 비교

**목적:** 이해 부채를 찾아 장부에 남기고, 복습 · 공부를 제안한다. "몇 번 물었나 · 이해했나"는 **전부 우리 장부에** 둔다. 지식 저장소는 읽기만 하고, 사용자가 승인한 새 노트만 쓴다.

입력: 사용자가 명령과 함께 준 입력 — 용어 하나 또는 목록. `/l-plan` · `/l-design` · `/l-build`가 넘긴 후보일 수도 있다 (그때는 작업 ID도 함께).

> ⚠ 이 프로젝트는 지식 저장소가 없어 배우는 선로가 꺼져 있다. 사용자에게 알리고 `/l-init`을 다시 실행해 `knowledge`를 설정할지 묻는다. 그 전까지는 용어를 설명만 하고 카드는 만들지 않는다.
