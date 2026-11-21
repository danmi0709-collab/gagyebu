"""손글씨 쓰기 종이(PDF) 생성기. 결과: template.pdf, layout.json"""
import json, os
import cv2, numpy as np
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
pdfmetrics.registerFont(TTFont("KR", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", subfontIndex=0))

from fontTools.ttLib import TTFont as _FT
from fontTools.pens.boundsPen import BoundsPen
_f = _FT("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", fontNumber=0)
_cmap, _gs, _upm = _f.getBestCmap(), _f.getGlyphSet(), _f["head"].unitsPerEm
def ink_center_y(ch, size_pt):
    """글자 모양(잉크)의 세로 중심이 글꼴 기준선에서 위로 몇 pt 떨어져 있는지"""
    bp = BoundsPen(_gs); _gs[_cmap[ord(ch)]].draw(bp)
    if bp.bounds is None: return size_pt * 0.35
    return (bp.bounds[1] + bp.bounds[3]) / 2 / _upm * size_pt

# ---- 글자 목록 -------------------------------------------------------------
JAMO = list("ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎㅏㅑㅓㅕㅗㅛㅜㅠㅡㅣ")
DIGITS = list("0123456789")
SYM1 = list(".,!?~^:;-()/'\"")
SYL1 = list("나는이가을를에서도한하고요다지아어네응그안해좋오")  # 1쪽(시험지)용 24자

SYL_REST = """
각 간 갈 감 갑 강 같 개 거 건 걸 검 것 게 겨 격 견 결 경 계 곡 곤 골 공 과 관 광 교 구 국 군 궁 권 귀 규 극 근 글 금 급 기 긴 길 김 까 깐 깜 께 꼭 꽃 꾸 꿈 끝 끼 갔 겠 걱 괜
낙 난 날 남 낮 내 낼 너 널 넓 넘 녀 년 노 놀 농 높 누 눈 느 늘 능 니 님 녁 냥 넹 넵
단 달 담 답 당 대 더 덕 던 데 독 돈 돌 동 되 두 둘 뒤 드 득 든 듯 들 등 디 따 딸 때 떠 또 뜻 띠 떻 됐
라 락 란 람 랑 래 량 러 려 력 련 렇 레 로 록 론 롭 료 루 류 률 르 리 린 림 립
마 막 만 많 말 맘 맛 망 맞 매 먹 먼 멀 메 며 면 명 모 목 몰 몸 못 무 문 물 뭐 미 민 밀 및 몇 뭔
바 박 반 받 발 밤 밥 방 배 백 버 번 벌 법 베 변 별 병 보 복 본 볼 봄 봐 부 북 분 불 비 빈 빌 빠 빨 뻐 뽑 뿐
사 산 살 삼 상 새 색 생 선 설 성 세 소 속 손 솔 쇼 수 숙 순 술 쉬 스 슬 습 시 식 신 실 심 십 싶 싸 써 쓰 씨 송 싫 샀 썼
악 알 암 앞 애 야 약 양 억 언 얼 없 엄 업 여 역 연 열 영 예 온 올 와 완 왔 왜 외 용 우 운 울 움 원 월 위 유 은 음 의 인 일 임 입 있 았 었 않 엽 워 엥
자 작 잔 잠 장 재 저 적 전 절 점 정 제 조 족 존 좀 종 주 죽 준 줄 중 즐 증 직 진 질 집 짜 짧 쪽 찌 잘 잖 죄 줘 졸
차 착 참 창 채 책 처 천 철 첫 청 체 초 촌 총 최 추 축 출 춤 충 치 친 칠 찮
카 커 컴 케 코 콩 쿠 크 큰 키 톡
타 탁 탄 탈 태 터 택 테 토 통 퇴 투 특 틀 티 팅
파 판 팔 패 팬 퍼 페 편 평 폐 포 폭 표 푸 풀 품 풍 프 피 필 쁘
학 할 함 합 항 햇 행 향 허 헤 현 형 호 혼 홈 화 확 환 활 황 회 후 훈 휴 흐 흔 힘 했 헐 흠 헉
""".split()
SYL_REST = [s for s in dict.fromkeys(SYL_REST) if s not in SYL1]
assert all(len(s) == 1 and 0xAC00 <= ord(s) <= 0xD7A3 for s in SYL_REST + SYL1)

ASCII_ALL = [chr(c) for c in range(33, 127)]
ASCII_REST = [c for c in ASCII_ALL if c not in DIGITS + SYM1]

def kind(ch):
    if ch in JAMO: return "jamo"
    if ord(ch) < 128: return "latin"
    return "hangul"

page1 = JAMO + DIGITS + SYM1 + SYL1
rest = ASCII_REST + SYL_REST
COLS, ROWS = 8, 9
PER = COLS * ROWS
assert len(page1) == PER, len(page1)
pages = [page1] + [rest[i:i+PER] for i in range(0, len(rest), PER)]

# ---- 치수(mm, 종이 왼쪽 위가 원점) --------------------------------------------
PW, PH = 210, 297
MK = 14                         # 표식 크기
MK_POS = [(8, 8), (PW-8-MK, 8), (8, PH-8-MK), (PW-8-MK, PH-8-MK)]  # TL,TR,BL,BR
GX, GY = 15, 24                 # 격자 시작
CW, CH = 22.5, 27.5             # 칸 크기
LABEL = 5.5                     # 안내 글자 띠 높이
BOX = 21.0                      # 쓰는 칸(정사각형)
# 쓰는 칸 안의 기준선(칸 위에서부터 mm). 칸 아래에서 20% = 글자 바닥선(baseline)
BASE = BOX * 0.80
CAP = BOX * 0.10
XH = BOX * 0.80 - BOX * 0.48

dic = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
layout = {"paper_mm": [PW, PH], "box_mm": BOX, "baseline_from_top_mm": BASE,
          "markers_mm": MK_POS, "marker_size_mm": MK, "pages": []}

c = canvas.Canvas(os.path.join(HERE, "template.pdf"), pagesize=(PW*2.8346456693, PH*2.8346456693))
S = 2.8346456693  # mm -> pt
def X(mm): return mm * S
def Y(mm): return (PH - mm) * S

for p, chars in enumerate(pages):
    ids = [4*p + k for k in range(4)]
    for (mx, my), mid in zip(MK_POS, ids):
        img = cv2.aruco.generateImageMarker(dic, mid, 240)
        c.drawImage(ImageReader(Image.fromarray(img)), X(mx), Y(my+MK), X(MK), X(MK))
    c.setFillGray(0.15)
    c.setFont("KR", 11)
    title = "내 손글씨 폰트 쓰기 종이  %d / %d쪽" % (p+1, len(pages)) + ("  (시험지: 이것부터!)" if p == 0 else "")
    c.drawString(X(26), Y(13), title)
    c.setFont("KR", 7.5); c.setFillGray(0.35)
    c.drawString(X(26), Y(18), "진한 볼펜으로, 칸 안에 크게. 선을 넘지 않게. 회색 글자는 '이걸 써라'는 안내예요.")
    c.drawString(X(26), Y(21.5), "영문은 아래쪽 진한 줄(바닥선)에 앉혀서 쓰세요. 사진은 네 모서리 네모가 다 나오게 위에서 똑바로.")
    pcells = []
    for i, ch in enumerate(chars):
        r, col = divmod(i, COLS)
        x0 = GX + col*CW; yt = GY + r*CH
        bx = x0 + (CW - BOX) / 2; by = yt + LABEL
        # 안내 글자(작게, 회색)
        c.setFillGray(0.3); c.setFont("KR", 12)
        c.drawString(X(x0+1.2), Y(yt + LABEL/2) - ink_center_y(ch, 12), ch)
        # 쓰는 칸 테두리
        c.setStrokeGray(0.78); c.setLineWidth(0.6)
        c.rect(X(bx), Y(by+BOX), X(BOX), X(BOX))
        c.setStrokeGray(0.86); c.setLineWidth(0.4); c.setDash(1.5, 1.5)
        if kind(ch) == "latin":
            c.setStrokeGray(0.6); c.setDash()
            c.line(X(bx), Y(by+BASE), X(bx+BOX), Y(by+BASE))      # 바닥선
            c.setStrokeGray(0.86); c.setDash(1.5, 1.5)
            c.line(X(bx), Y(by+CAP), X(bx+BOX), Y(by+CAP))        # 대문자 높이
            c.line(X(bx), Y(by+BASE-BOX*0.32), X(bx+BOX), Y(by+BASE-BOX*0.32))  # 소문자 높이
        else:
            c.line(X(bx+BOX/2), Y(by), X(bx+BOX/2), Y(by+BOX))
            c.line(X(bx), Y(by+BOX/2), X(bx+BOX), Y(by+BOX/2))
        c.setDash()
        pcells.append({"char": ch, "kind": kind(ch), "row": r, "col": col, "box_mm": [bx, by, BOX, BOX]})
    layout["pages"].append({"page": p+1, "marker_ids": ids, "cells": pcells})
    c.showPage()
c.save()
json.dump(layout, open(os.path.join(HERE, "layout.json"), "w"), ensure_ascii=False, indent=1)
print("pages:", len(pages), "| 한글:", len(SYL1)+len(SYL_REST), "| 영문·기호:", len(ASCII_ALL), "| 자모:", len(JAMO))
