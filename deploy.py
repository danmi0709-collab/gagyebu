"""
가계부 배포 자동화 스크립트
실행: python deploy.py "커밋 메시지"
     python deploy.py  (메시지 없으면 직접 입력)
"""
import re, sys, io, subprocess
from pathlib import Path

# Windows 콘솔 한국어 출력
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE   = Path(__file__).parent
SRC    = BASE / "가계부.html"
SHARED = BASE / "가계부_공유용.html"
IDX    = BASE / "index.html"
SIDX   = BASE / "share" / "index.html"

# ── 색상 ──
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"
C = "\033[96m"; B = "\033[1m";  X = "\033[0m"

def step(n, title):
    print(f"\n{C}{B}[{n}/4] {title}{X}")
    print("─" * 45)

def ok(msg):   print(f"  {G}✓ {msg}{X}")
def fail(msg): print(f"  {R}✗ {msg}{X}")
def warn(msg): print(f"  {Y}! {msg}{X}")
def info(msg): print(f"    {msg}")

def run(cmd):
    """git 명령어 실행, (stdout, returncode) 반환"""
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       cwd=str(BASE))
    return r.stdout.strip(), r.returncode

# ══════════════════════════════════════════
# STEP 1 — SYNC
# ══════════════════════════════════════════
def do_sync():
    step(1, "공유용 파일 동기화 (sync)")

    if not SRC.exists():
        fail(f"가계부.html 없음: {SRC}")
        return False

    c = SRC.read_text(encoding="utf-8")

    # localStorage 키 변환
    KEY_MAP = [
        ("hanna_transactions",         "my_transactions"),
        ("hanna_budget",               "my_budget"),
        ("hanna_yeardata",             "my_yeardata"),
        ("hanna_subscriptions",        "my_subscriptions"),
        ("hanna_assets",               "my_assets"),
        ("hanna_gdrive_token",         "my_gdrive_token"),
        ("hanna_gdrive_fileid",        "my_gdrive_fileid"),
        ("hanna_last_upload",          "my_last_upload"),
        ("hanna_catmonth",             "my_catmonth"),
        ("hanna_currentyear",          "my_currentyear"),
        ("hanna_theme",                "my_theme"),
        ("hanna_nickname",             "my_nickname"),
        ("hanna_annual_budget",        "my_annual_budget"),
        ("hanna_tx_order",             "my_tx_order"),
        ("hanna_merchant_cats",        "my_merchant_cats"),
        ("hanna_sheets_url",           "my_sheets_url"),
        ("hanna_sub_auto_month",       "my_sub_auto_month"),
        ("hanna_formula_man_migrated", "my_formula_man_migrated"),
    ]
    replaced = 0
    for old, new in KEY_MAP:
        if old in c:
            c = c.replace(old, new)
            replaced += 1
    ok(f"localStorage 키 {replaced}개 변환")

    # 텍스트 변환
    c = c.replace("한나의 가계부", "나만의 가계부")
    c = re.sub(r"이번 달 잔액 \(한나\)", "이번 달 잔액", c)
    c = c.replace("한나", "나")
    ok("텍스트 변환 (한나 → 나)")

    # IS_SHARED 플래그
    if "const IS_SHARED = false;" in c:
        c = c.replace("const IS_SHARED = false;", "const IS_SHARED = true;")
        ok("IS_SHARED = true 설정")
    else:
        warn("IS_SHARED = false 원본 없음 (이미 변환됐을 수 있음)")

    # OG + PWA 메타태그 주입
    OG_BLOCK = """
<!-- Open Graph (카카오톡·SNS 미리보기) -->
<meta property="og:type" content="website">
<meta property="og:site_name" content="나만의 가계부">
<meta property="og:title" content="나만의 가계부 💰">
<meta property="og:description" content="설치 없이 브라우저에서 바로 쓰는 무료 가계부. 수입·지출·저축 관리, 자산 추이 차트, 연예산 계획까지. 내 데이터는 내 기기에만 저장됩니다.">
<meta property="og:image" content="https://danmi0709-collab.github.io/gagyebu/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="https://danmi0709-collab.github.io/gagyebu/share">
<meta name="description" content="설치 없이 브라우저에서 바로 쓰는 무료 가계부. 수입·지출·저축 관리, 자산 추이 차트, 연예산 계획까지.">
<!-- 카카오톡 전용 -->
<meta property="kakao:title" content="나만의 가계부 💰">
<meta property="kakao:description" content="설치 없이 바로 쓰는 무료 가계부. 내 데이터는 내 기기에만 저장됩니다.">
<meta property="kakao:image" content="https://danmi0709-collab.github.io/gagyebu/og-image.png">
<!-- PWA (홈 화면 설치) -->
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#c07a3a">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="가계부">
<link rel="apple-touch-icon" href="icon-192.png">"""

    if "og:image" not in c:
        c = re.sub(r"(<title>[^<]*</title>)", r"\1" + OG_BLOCK, c)
        ok("OG + PWA 메타태그 주입")
    else:
        ok("OG + PWA 메타태그 이미 있음 (유지)")

    # 저장
    SHARED.write_text(c, encoding="utf-8")
    SIDX.write_text(c, encoding="utf-8")
    IDX.write_text(SRC.read_text(encoding="utf-8"), encoding="utf-8")
    ok(f"파일 저장: 가계부_공유용.html / share/index.html / index.html")
    return True


# ══════════════════════════════════════════
# STEP 2 — CHECK
# ══════════════════════════════════════════
def do_check():
    step(2, "공유앱 이상 없는지 검사 (check)")

    content = SHARED.read_text(encoding="utf-8")
    lines   = content.splitlines()
    passed  = True

    # hanna_ 잔존 검사
    hits = []
    for i, line in enumerate(lines, 1):
        if re.search(r"hanna_\w+", line):
            stripped = line.strip()
            if not re.match(r"^\s*(//|<!--|#)", stripped):
                keys = re.findall(r"hanna_\w+", stripped)
                hits.append((i, keys, stripped[:80]))

    if not hits:
        ok("hanna_ 키 없음")
    else:
        passed = False
        unique = sorted({k for _, ks, _ in hits for k in ks})
        fail(f"hanna_ 키 {len(hits)}곳 발견 → 아래 규칙을 KEY_MAP에 추가하세요")
        for k in unique:
            info(f'("{k}", "{k.replace("hanna_","my_")}"),')

    # IS_SHARED 확인
    if "const IS_SHARED = true;" in content:
        ok("IS_SHARED = true")
    else:
        passed = False
        fail("IS_SHARED = true 없음!")

    # OG 태그 확인
    if "og:image" in content:
        ok("OG 메타태그 있음")
    else:
        passed = False
        fail("OG 메타태그 없음!")

    # PWA 확인
    if 'rel="manifest"' in content:
        ok("PWA manifest 있음")
    else:
        warn("PWA manifest 없음 (선택사항)")

    return passed


# ══════════════════════════════════════════
# STEP 3 — GIT STATUS
# ══════════════════════════════════════════
def do_git_status():
    step(3, "변경 파일 확인 (git status)")

    out, _ = run(["git", "status", "--short"])
    if not out:
        warn("변경된 파일 없음 — push 생략")
        return []

    changed = []
    for line in out.splitlines():
        info(line)
        fname = line[3:].strip().strip('"')
        changed.append(fname)
    return changed


# ══════════════════════════════════════════
# STEP 4 — GIT COMMIT + PUSH
# ══════════════════════════════════════════
def do_push(msg, changed):
    step(4, "GitHub 배포 (commit + push)")

    # add
    run(["git", "add",
         "가계부.html", "가계부_공유용.html",
         "index.html", "share/index.html"])
    # 기타 변경 파일 추가
    for f in changed:
        run(["git", "add", f])

    # commit
    _, rc = run(["git", "commit", "-m", msg])
    if rc != 0:
        warn("커밋할 내용 없음 (이미 최신)")
    else:
        ok(f"커밋: {msg}")

    # push
    out, rc = run(["git", "push", "origin", "main"])
    if rc == 0:
        ok("GitHub push 완료")
        ok("https://danmi0709-collab.github.io/gagyebu/share")
        return True
    else:
        fail("push 실패 — 재시도 중...")
        for attempt in range(1, 4):
            info(f"재시도 {attempt}/3")
            _, rc2 = run(["git", "push", "origin", "main"])
            if rc2 == 0:
                ok("push 성공!")
                return True
        fail("push 3회 실패. 네트워크 확인 필요")
        return False


# ══════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════
def main():
    print(f"\n{B}{C}{'═'*45}")
    print(f"  가계부 배포 자동화  deploy.py")
    print(f"{'═'*45}{X}")

    # 커밋 메시지 입력
    if len(sys.argv) > 1:
        commit_msg = " ".join(sys.argv[1:])
    else:
        print(f"\n{Y}커밋 메시지를 입력하세요 (예: 탭3 차트 색상 수정){X}")
        commit_msg = input("  > ").strip()
        if not commit_msg:
            commit_msg = "update: 가계부 앱 업데이트"

    # 4단계 실행
    if not do_sync():
        print(f"\n{R}SYNC 실패. 종료.{X}\n"); sys.exit(1)

    if not do_check():
        print(f"\n{R}CHECK 실패. push 중단. 위 항목 수정 후 재실행하세요.{X}\n")
        sys.exit(1)

    changed = do_git_status()

    if changed:
        ok_push = do_push(commit_msg, changed)
    else:
        ok_push = True

    # 최종 요약
    print(f"\n{B}{'═'*45}{X}")
    if ok_push:
        print(f"{G}{B}  배포 완료!{X}")
        print(f"  {C}https://danmi0709-collab.github.io/gagyebu/share{X}")
    else:
        print(f"{R}{B}  배포 실패 — 로그 확인 필요{X}")
    print(f"{B}{'═'*45}{X}\n")


if __name__ == "__main__":
    main()
