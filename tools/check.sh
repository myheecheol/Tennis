#!/usr/bin/env bash
# 설계 산출물 전체 검사 + 생성물 갱신. 커밋 전에 이걸 돌린다.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "── 1/5 커리큘럼 검증 + 인덱스 생성"
python3 tools/curriculum.py

echo
echo "── 2/5 카드 검증"
python3 tools/validate_cards.py data/cards/*.json

echo
echo "── 3/5 카드 ↔ 인덱스 대조"
python3 tools/check_consistency.py

echo
echo "── 4/5 생성 문서 갱신"
python3 tools/render_curriculum.py
python3 tools/render_exemplars.py

echo
echo "── 5/5 웹 페이지 빌드"
python3 web/build.py | head -3

echo
echo "✅ 전부 통과"
