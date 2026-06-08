"""공유앱에서 sheetsSection을 완전히 제거하고 모달 정리"""
import sys, io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = Path(__file__).parent

def remove_div_by_id(html, div_id):
    """id로 div를 찾아 중첩 구조까지 완전히 제거"""
    marker = f'<div id="{div_id}">'
    start = html.find(marker)
    if start == -1:
        return html, False

    # 앞쪽 공백/줄바꿈도 함께 제거
    trim_start = start
    while trim_start > 0 and html[trim_start-1] in (' ', '\t', '\n', '\r'):
        trim_start -= 1

    depth = 0
    i = start
    while i < len(html):
        if html[i:i+4] == '<div':
            depth += 1
            i += 4
        elif html[i:i+6] == '</div>':
            depth -= 1
            i += 6
            if depth == 0:
                end = i
                break
        else:
            i += 1

    result = html[:trim_start] + html[end:]
    return result, True

# 파일 목록
targets = [
    BASE / "가계부_공유용.html",
    BASE / "share" / "index.html",
]

for path in targets:
    c = path.read_text(encoding="utf-8")
    original_len = len(c)

    # 1. sheetsSection 제거
    c, removed = remove_div_by_id(c, "sheetsSection")
    if removed:
        print(f"OK  sheetsSection 제거 ({original_len - len(c)}자 삭제)")
    else:
        print("    sheetsSection 이미 없음")

    # 2. 모달 타이틀
    c = c.replace("⚙️ 구글 시트 연동 설정", "⚙️ 설정")
    c = c.replace("<!-- 설정 모달 (구글 시트 연동) -->", "<!-- 설정 모달 -->")

    # 3. 닉네임 섹션 기본 표시
    c = c.replace(
        'id="nicknameSettingsSection" style="display:none;',
        'id="nicknameSettingsSection" style="display:block;'
    )

    # 4. 헤더 syncStatus 제거
    import re
    before = len(c)
    c = re.sub(r'\s*<div class="sync-status" id="syncStatus"></div>', '', c)
    if len(c) < before:
        print("OK  syncStatus 헤더 제거")

    path.write_text(c, encoding="utf-8")
    print(f"저장: {path.name}")
    print()

print("완료!")
