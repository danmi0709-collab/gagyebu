"""칸별 잉크 PNG들 -> 손글씨 폰트(.ttf).
사용: python3 -I build_font.py <cells폴더> <출력.ttf> [폰트이름]
cells폴더 안의 p*_cells.json 을 모두 읽는다(여러 쪽 지원)."""
import sys, os, json, glob
import numpy as np, cv2, potrace
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen

UP = 4            # 윤곽 따기 전 확대 배율
BOX_PX = 210      # 쓰는 칸 한 변(px) = 폰트 1000단위
K = 1000 / BOX_PX
HANGUL_H = 700    # 한글 글자 높이 목표(단위)
DIGIT_H = 640     # 숫자·영문 높이 목표(대문자 높이쯤)
MAX_SCALE = 2.6
BOLD_PX = 5       # 윤곽 따기 전 살짝 굵게(확대 이미지 기준 px)

def trace_cell(png, margin):
    ink = cv2.imread(png, 0)
    if ink is None or (ink > 0).sum() < 3: return None
    big = cv2.resize(ink, None, fx=UP, fy=UP, interpolation=cv2.INTER_CUBIC)
    big = cv2.GaussianBlur(big, (0, 0), 1.6)
    big = (big > 110).astype(np.uint8) * 255
    if BOLD_PX: big = cv2.dilate(big, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*BOLD_PX+1,)*2))
    pl = potrace.Bitmap(255 - big).trace(turdsize=3, alphamax=1.1, opticurve=True, opttolerance=0.3)
    conv = lambda p: ((p.x / UP - margin) * K, (margin + BOX_PX - p.y / UP) * K - 200)  # 칸 -> 폰트좌표
    contours = []
    for curve in pl:
        segs = [("M", conv(curve.start_point))]
        for s in curve.segments:
            if s.is_corner: segs += [("L", conv(s.c)), ("L", conv(s.end_point))]
            else: segs.append(("C", conv(s.c1), conv(s.c2), conv(s.end_point)))
        contours.append(segs)
    return contours

def bbox(contours):
    pts = [p for c in contours for s in c for p in s[1:]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)

def transform(contours, fx):
    return [[(s[0],) + tuple(fx(*p) for p in s[1:]) for s in c] for c in contours]

CONS = "ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ"
BLEND = 0.85   # 높이 차이를 줄이는 정도(1이면 완전히 같게, 0이면 그대로)

def fit_height(cs, target, center, max_w=980):
    """글자 높이를 target 쪽으로 맞추고 세로 중심을 center에 둔다(가로폭은 max_w 넘지 않게)."""
    x0, y0, x1, y1 = bbox(cs); h = max(y1 - y0, 1); w = max(x1 - x0, 1)
    k = 1 + BLEND * (target / h - 1)
    k = max(0.6, min(1.6, k, max_w / w))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return transform(cs, lambda x, y: ((x - cx) * k + cx, (y - cy) * k + center))

def fit_digit(cs, target):
    """숫자 높이를 맞추고 바닥을 기준선(y=0)에 앉힌다."""
    x0, y0, x1, y1 = bbox(cs); h = max(y1 - y0, 1)
    k = max(0.6, min(1.6, 1 + BLEND * (target / h - 1)))
    return transform(cs, lambda x, y: (x * k, (y - y0) * k))

# 기호가 놓일 높이(숫자 높이 DIGIT_H의 비율). c=세로 중심, b=아래끝, t=위끝
SYM_ANCHOR = {"-": ("c", 0.42), "~": ("c", 0.55), "(": ("c", 0.40), ")": ("c", 0.40), "/": ("c", 0.40),
              ".": ("b", 0.0), ",": ("t", 0.15), ":": ("b", 0.0), ";": ("b", -0.12),
              "'": ("t", 1.0), '"': ("t", 1.0), "^": ("t", 1.0)}

def place_symbol(cs, ch):
    mode, r = SYM_ANCHOR[ch]; target = r * DIGIT_H
    x0, y0, x1, y1 = bbox(cs)
    cur = {"c": (y0 + y1) / 2, "b": y0, "t": y1}[mode]
    return transform(cs, lambda x, y: (x, y + target - cur))

def to_glyph(contours):
    rec = RecordingPen()
    for c in contours:
        rec.moveTo(c[0][1])
        for s in c[1:]:
            if s[0] == "L": rec.lineTo(s[1])
            else: rec.curveTo(s[1], s[2], s[3])
        rec.closePath()
    # 바깥 윤곽이 시계방향이 되도록(TrueType 규칙)
    best, area_best = None, 0
    for c in contours:
        pts = [c[0][1]] + [s[-1] for s in c[1:]]
        a = sum(x1*y2 - x2*y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])) / 2
        if abs(a) > abs(area_best): area_best = a
    pen = TTGlyphPen(None)
    target = ReverseContourPen(Cu2QuPen(pen, 1.0)) if area_best > 0 else Cu2QuPen(pen, 1.0)
    rec.replay(target)
    return pen.glyph()

def main(cells_dir, out_ttf, family="MyHand"):
    items = []
    for jf in sorted(glob.glob(os.path.join(cells_dir, "p*_cells.json"))):
        for m in json.load(open(jf)):
            cs = trace_cell(os.path.join(cells_dir, m["file"]), m["margin_px"])
            if cs: items.append((m["char"], m["kind"], cs))
    print("윤곽 딴 글자 수:", len(items))
    # 그룹별 확대 비율(같은 그룹은 모두 같은 비율 -> 손글씨 크기 차이 유지)
    def med(kinds, only=None):
        hs = [bbox(c)[3] - bbox(c)[1] for ch, k, c in items if k in kinds and (only is None or ch in only)]
        return float(np.median(hs)) if hs else None
    hh = med(("hangul",)) or med(("jamo",))
    dh = med(("latin",), only="0123456789")
    s_h = min(MAX_SCALE, HANGUL_H / hh) if hh else 1.0
    s_l = min(MAX_SCALE, DIGIT_H / dh) if dh else 1.0
    print(f"한글 중간 높이 {hh and round(hh)} -> 확대 x{s_h:.2f} | 숫자 중간 높이 {dh and round(dh)} -> 확대 x{s_l:.2f}")

    glyphs, metrics, cmap, order = {}, {}, {}, [".notdef", "space"]
    pen = TTGlyphPen(None)
    for (x0, y0, x1, y1) in ((60, -100, 740, 800), (130, -30, 670, 730)):
        pass
    outer = [(60, -100), (60, 800), (740, 800), (740, -100)]; inner = outer[::-1]
    inner = [(130, -30), (670, -30), (670, 730), (130, 730)]
    pen.moveTo(outer[0]); [pen.lineTo(p) for p in outer[1:]]; pen.closePath()
    pen.moveTo(inner[0]); [pen.lineTo(p) for p in inner[1:]]; pen.closePath()
    glyphs[".notdef"] = pen.glyph(); metrics[".notdef"] = 800
    glyphs["space"] = TTGlyphPen(None).glyph(); metrics["space"] = 450
    cmap[0x20] = "space"
    for ch, kind, cs in items:
        name = "uni%04X" % ord(ch)
        if kind == "latin":
            s = s_l
            cs = transform(cs, lambda x, y: (x * s, y * s))            # 바닥선(y=0) 기준 확대
            if ch in "0123456789!?": cs = fit_digit(cs, DIGIT_H)
            elif ch in SYM_ANCHOR: cs = place_symbol(cs, ch)
            xmin, _, xmax, _ = bbox(cs)
            cs = transform(cs, lambda x, y: (x - xmin + 70, y))
            adv = max(260, int(xmax - xmin + 140))
        else:
            s = s_h
            cs = transform(cs, lambda x, y: ((x - 500) * s + 500, (y - 300) * s + 330))  # 칸 중심 기준 확대
            if kind == "hangul": cs = fit_height(cs, HANGUL_H, 330)
            elif ch in CONS: cs = fit_height(cs, HANGUL_H * 0.72, 350)
            else:
                _, y0_, _, y1_ = bbox(cs); cs = transform(cs, lambda x, y: (x, y - (y0_ + y1_) / 2 + 350))
            xmin, _, xmax, _ = bbox(cs)
            w = xmax - xmin
            adv = max(1000, int(w + 90)) if kind == "hangul" else max(520, int(w + 140))
            dx = (adv - w) / 2 - xmin
            cs = transform(cs, lambda x, y: (x + dx, y))
        glyphs[name] = to_glyph(cs); metrics[name] = adv
        cmap[ord(ch)] = name; order.append(name)
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(order if False else [".notdef", "space"] + order[2:])
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    glyf = fb.font["glyf"]; hm = {}
    for n, g in glyphs.items():
        g.recalcBounds(glyf); hm[n] = (metrics[n], getattr(g, "xMin", 0) if g.numberOfContours else 0)
    fb.setupHorizontalMetrics(hm)
    fb.setupHorizontalHeader(ascent=880, descent=-240)
    fb.setupNameTable({"familyName": family, "styleName": "Regular"})
    fb.setupOS2(sTypoAscender=880, sTypoDescender=-240, usWinAscent=1000, usWinDescent=300, sxHeight=480, sCapHeight=700)
    fb.setupPost(); fb.save(out_ttf)
    print("폰트 저장:", out_ttf, "| 글자 수:", len(cmap))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "MyHand")
