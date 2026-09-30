#!/usr/bin/env bash
# 설계 산출물 전체 검사 + 생성물 갱신. 커밋 전에 이걸 돌린다.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "── 1/6 커리큘럼 검증 + 인덱스 생성"
python3 tools/curriculum.py

echo
echo "── 2/6 카드 검증 + 검증기 회귀 테스트"
python3 tools/validate_cards.py data/cards/*.json
python3 tools/test_validator.py

echo
echo "── 3/6 카드 ↔ 인덱스 대조"
python3 tools/check_consistency.py

echo
echo "── 4/6 생성 문서 갱신"
python3 tools/render_curriculum.py
python3 tools/render_exemplars.py

echo
echo "── 5/6 웹 페이지 빌드"
python3 web/build.py | sed -n "1,3p"

echo
echo "── 6/6 웹 스모크 테스트 (헤드리스 Chromium — 없으면 건너뜀)"
python3 tools/web_smoke.py

echo
echo "✅ 전부 통과"
