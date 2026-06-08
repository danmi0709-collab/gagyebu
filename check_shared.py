"""
공유앱 데이터 분리 검사 스크립트
실행: python check_shared.py
"""
import re, sys, io
from pathlib import Path

# Windows 콘솔 한국어 출력 설정
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE    = Path(__file__).parent
SHARED  = BASE / "가계부_공유용.html"

# ── 검사할 항목 ──
CHECKS = {
    "hanna_ 키 잔존": {
        "pattern": r"hanna_\w+",
        "exclude": r"^\s*(//|<!--|#)",   # 주석 줄 제외
        "level": "FAIL",
    },
    "IS_SHARED = false": {
        "pattern": r"const IS_SHARED\s*=\s*false",
        "level": "FAIL",
    },
    "IS_SHARED = true 없음": {
        "pattern": r"const IS_SHARED\s*=\s*true",
        "must_exist": True,   # 이 패턴이 '있어야' 통과
        "level": "FAIL",
    },
}

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def banner(text, color=CYAN):
    line = "=" * 50
    print(f"\n{color}{BOLD}{line}")
    print(f"  {text}")
    print(f"{line}{RESET}\n")

def main():
    if not SHARED.exists():
        print(f"{RED}[ERROR] 파일을 찾을 수 없어요: {SHARED}{RESET}")
        return

    lines = SHARED.read_text(encoding="utf-8").splitlines()
    total_fail = 0

    banner("공유앱 키 누락 검사")
    print(f"파일: {SHARED.name}  ({len(lines):,} 줄)\n")

    # ── 1. hanna_ 키 잔존 검사 ──
    hits = []
    for i, line in enumerate(lines, 1):
        if re.search(r"hanna_\w+", line):
            stripped = line.strip()
            if not re.match(r"^\s*(//|<!--|#)", stripped):
                keys = re.findall(r"hanna_\w+", stripped)
                hits.append((i, keys, stripped[:90]))

    if not hits:
        print(f"{GREEN}[PASS] hanna_ 키 없음{RESET}")
    else:
        total_fail += 1
        unique_keys = sorted({k for _, keys, _ in hits for k in keys})
        print(f"{RED}[FAIL] hanna_ 키 {len(hits)}곳 발견!{RESET}\n")
        print(f"{YELLOW}누락된 키 목록:{RESET}")
        for k in unique_keys:
            my_k = k.replace("hanna_", "my_")
            print(f"  {RED}{k}{RESET}  →  {GREEN}{my_k}{RESET}")
        print(f"\n{YELLOW}발견된 위치:{RESET}")
        for ln, keys, text in hits[:10]:
            print(f"  Line {ln:5d}: {text}")
        if len(hits) > 10:
            print(f"  ... 외 {len(hits)-10}곳")
        print(f"\n{CYAN}sync_shared.ps1 에 추가할 변환 규칙:{RESET}")
        for k in unique_keys:
            my_k = k.replace("hanna_", "my_")
            print(f'  $c = $c -replace "{k}", "{my_k}"')

    # ── 2. IS_SHARED 플래그 확인 ──
    print()
    content = SHARED.read_text(encoding="utf-8")
    if "const IS_SHARED = true;" in content:
        print(f"{GREEN}[PASS] IS_SHARED = true  (정상){RESET}")
    elif "const IS_SHARED = false;" in content:
        total_fail += 1
        print(f"{RED}[FAIL] IS_SHARED = false  → sync_shared.ps1 재실행 필요{RESET}")
    else:
        total_fail += 1
        print(f"{YELLOW}[WARN] IS_SHARED 플래그 없음{RESET}")

    # ── 3. OG 태그 확인 ──
    print()
    if "og:image" in content:
        print(f"{GREEN}[PASS] OG 메타태그 있음  (카카오톡 미리보기){RESET}")
    else:
        total_fail += 1
        print(f"{RED}[FAIL] OG 메타태그 없음!{RESET}")

    # ── 4. PWA manifest 확인 ──
    print()
    if 'rel="manifest"' in content:
        print(f"{GREEN}[PASS] PWA manifest 링크 있음{RESET}")
    else:
        total_fail += 1
        print(f"{YELLOW}[WARN] PWA manifest 링크 없음{RESET}")

    # ── 최종 결과 ──
    print()
    if total_fail == 0:
        print(f"{GREEN}{BOLD}{'='*50}")
        print(f"  전체 통과! 공유앱 이상 없어요.")
        print(f"{'='*50}{RESET}")
    else:
        print(f"{RED}{BOLD}{'='*50}")
        print(f"  {total_fail}개 항목 실패. sync_shared.ps1 재실행 필요")
        print(f"{'='*50}{RESET}")
    print()

if __name__ == "__main__":
    main()
