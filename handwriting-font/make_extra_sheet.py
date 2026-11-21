"""보정·추가 쓰기 종이(PDF). 1~9쪽과 같은 규격(칸 크기·표식)이라 extract_page.py 로 그대로 처리된다.
사용: python3 -I make_extra_sheet.py <다시쓸글자.json> [추가글자수=자동]
결과: extra_sheet.pdf, layout.json 에 10쪽(필요하면 11쪽…) 추가"""
import json, os, sys
import cv2
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from fontTools.ttLib import TTFont as _FT
from fontTools.pens.boundsPen import BoundsPen

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
pdfmetrics.registerFont(TTFont("KR", FONT, subfontIndex=0))
_f = _FT(FONT, fontNumber=0); _cmap, _gs, _upm = _f.getBestCmap(), _f.getGlyphSet(), _f["head"].unitsPerEm
def ink_center_y(ch, size_pt):
    bp = BoundsPen(_gs); _gs[_cmap[ord(ch)]].draw(bp)
    return size_pt * 0.35 if bp.bounds is None else (bp.bounds[1] + bp.bounds[3]) / 2 / _upm * size_pt

# 카톡 대화에 자주 쓰는데 1~9쪽 목록에 없을 법한 글자(우선순위 순; 이미 있는 글자는 자동으로 뺀다)
EXTRA_PRIORITY = list("녕짱즘럼런냐히으죠밌슨봤씻걷뛰앉눕듣읽믿웃벗찍쌤잼꿀딱깡쿨킹윽엉흑뜨뭘겁꺼넌놔늦닭땅떡똑맨멍몽밖빵삐샘샤섭셔쉽슈싱쏘앙앗얘엇옷웬읍쟤젤졌줍짝쩌찜챙첨쳐칭캐켜콘쿵킥탐텐튀팡핑헬훨흥걔곧")

# ---- make_template.py 와 같은 규격 -------------------------------------------
PW, PH = 210, 297; MK = 14
MK_POS = [(8, 8), (PW-8-MK, 8), (8, PH-8-MK), (PW-8-MK, PH-8-MK)]
GX, GY = 15, 24; CW, CH = 22.5, 27.5; LABEL = 5.5; BOX = 21.0
COLS, ROWS = 8, 9; PER = COLS * ROWS; S = 2.8346456693

def main(rewrite_json, n_extra=None):
    layout = json.load(open(os.path.join(HERE, "layout.json")))
    have = {c["char"] for p in layout["pages"] if p["page"] <= 9 for c in p["cells"]}
    rewrite = [c for c in json.load(open(rewrite_json)) if c in have]
    # '좋'을 맨 앞(가장 먼저 쓰는 칸)으로
    rewrite.sort(key=lambda c: (c != "좋",))
    room = PER - len(rewrite) if n_extra is None else n_extra
    extras = [c for c in dict.fromkeys(EXTRA_PRIORITY) if c not in have][:max(room, 0)]
    chars = rewrite + extras
    pages = [chars[i:i+PER] for i in range(0, len(chars), PER)]
    base = 10
    layout["pages"] = [p for p in layout["pages"] if p["page"] < base]       # 이전에 만든 10쪽 이후는 지우고 다시
    c = canvas.Canvas(os.path.join(HERE, "extra_sheet.pdf"), pagesize=(PW*S, PH*S))
    X = lambda mm: mm * S; Y = lambda mm: (PH - mm) * S
    dic = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    for pi, pc in enumerate(pages):
        pno = base + pi
        ids = [4*(pno-1) + k for k in range(4)]
        for (mx, my), mid in zip(MK_POS, ids):
            c.drawImage(ImageReader(Image.fromarray(cv2.aruco.generateImageMarker(dic, mid, 240))), X(mx), Y(my+MK), X(MK), X(MK))
        c.setFillGray(0.15); c.setFont("KR", 11)
        c.drawString(X(26), Y(13), f"내 손글씨 폰트 보정·추가 종이  {pi+1} / {len(pages)}쪽")
        c.setFont("KR", 7.5); c.setFillGray(0.35)
        c.drawString(X(26), Y(18), f"앞의 {len(rewrite)}칸: 이미 쓴 글자인데 작게 써서, 이번엔 크게(칸의 3분의 2 이상) 다시 써 주세요. 나머지는 새 글자예요.")
        c.drawString(X(26), Y(21.5), "진한 볼펜으로, 칸 안에 크게. 선을 넘지 않게. 사진은 네 모서리 네모가 다 나오게 위에서 똑바로.")
        cells = []
        for i, ch in enumerate(pc):
            r, col = divmod(i, COLS); x0 = GX + col*CW; yt = GY + r*CH
            bx = x0 + (CW - BOX) / 2; by = yt + LABEL
            c.setFillGray(0.3); c.setFont("KR", 12)
            c.drawString(X(x0+1.2), Y(yt + LABEL/2) - ink_center_y(ch, 12), ch)
            if pi == 0 and i < len(rewrite):                    # 다시 쓰는 칸은 표시(작은 동그라미)
                c.setFillGray(0.55); c.circle(X(x0 + CW - 2.2), Y(yt + 2.6), 1.1*S, stroke=0, fill=1)
            c.setStrokeGray(0.78); c.setLineWidth(0.6); c.rect(X(bx), Y(by+BOX), X(BOX), X(BOX))
            c.setStrokeGray(0.86); c.setLineWidth(0.4); c.setDash(1.5, 1.5)
            c.line(X(bx+BOX/2), Y(by), X(bx+BOX/2), Y(by+BOX)); c.line(X(bx), Y(by+BOX/2), X(bx+BOX), Y(by+BOX/2)); c.setDash()
            cells.append({"char": ch, "kind": "hangul", "row": r, "col": col, "box_mm": [bx, by, BOX, BOX]})
        layout["pages"].append({"page": pno, "marker_ids": ids, "cells": cells,
                                "note": "rewrite+extra", "rewrite": pc[:max(0, len(rewrite) - pi*PER)] if pi == 0 else []})
        c.showPage()
    c.save()
    json.dump(layout, open(os.path.join(HERE, "layout.json"), "w"), ensure_ascii=False, indent=1)
    print(f"다시 쓸 글자 {len(rewrite)}자 + 추가 글자 {len(extras)}자 = {len(chars)}칸, {len(pages)}쪽")
    print("추가 글자:", "".join(extras)); print("다시 쓸 글자:", "".join(rewrite))

if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
