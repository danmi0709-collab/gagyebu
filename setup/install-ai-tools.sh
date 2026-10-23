#!/usr/bin/env bash
# Ponytail, Graphify, Headroom 설치 스크립트 (맥 / 리눅스 / 클라우드 세션 공용)
# 이미 설치된 건 건너뛰니까 여러 번 실행해도 괜찮다.
# 사용법: bash setup/install-ai-tools.sh

set -u
export PATH="$HOME/.local/bin:$PATH"

step() { printf '\n== %s\n' "$1"; }

step "uv"
if command -v uv >/dev/null 2>&1; then
  echo "이미 있음: $(uv --version)"
else
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

step "Ponytail (Claude Code 플러그인)"
if claude plugin list 2>/dev/null | grep -q "ponytail@ponytail"; then
  echo "이미 있음"
else
  claude plugin marketplace add DietrichGebert/ponytail --scope user
  claude plugin install ponytail@ponytail --scope user
fi

step "Graphify"
if command -v graphify >/dev/null 2>&1; then
  echo "이미 있음: $(graphify --version)"
else
  uv tool install graphifyy
fi
# 스킬 파일이 없을 때만 연결 작업 실행
if [ ! -f "$HOME/.claude/skills/graphify/SKILL.md" ]; then
  graphify install
fi

step "Headroom"
if command -v headroom >/dev/null 2>&1; then
  echo "이미 있음: $(headroom --version)"
else
  uv tool install --python 3.13 "headroom-ai[proxy,mcp]"
fi

step "결과"
claude plugin list 2>/dev/null | grep -A3 "ponytail@ponytail" || echo "ponytail 확인 실패"
graphify --version || echo "graphify 확인 실패"
headroom --version || echo "headroom 확인 실패"
