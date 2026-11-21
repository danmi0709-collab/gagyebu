"""자음·모음 부품으로 한글 글자를 조합한다(네가 쓴 글자에 없는 글자를 채우기 위해).
부품 = 1쪽에서 쓴 자음 14개·모음 10개. 글자 구조별 '자리'에 맞춰 배치하고, 획 굵기는 build_font 와 같은 방식으로 맞춘다.
사용(시험): python3 -I compose.py <cells폴더> <출력폴더> [목표굵기=46]"""
import sys, os, json, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
import build_font as bf

L_LIST = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
V_LIST = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
T_LIST = ["", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"]
DOUBLE = {"ㄲ": "ㄱㄱ", "ㄸ": "ㄷㄷ", "ㅃ": "ㅂㅂ", "ㅆ": "ㅅㅅ", "ㅉ": "ㅈㅈ"}
COMP_T = {"ㄳ": "ㄱㅅ", "ㄵ": "ㄴㅈ", "ㄶ": "ㄴㅎ", "ㄺ": "ㄹㄱ", "ㄻ": "ㄹㅁ", "ㄼ": "ㄹㅂ", "ㄽ": "ㄹㅅ", "ㄾ": "ㄹㅌ", "ㄿ": "ㄹㅍ", "ㅀ": "ㄹㅎ", "ㅄ": "ㅂㅅ", **DOUBLE}
VERT = set("ㅏㅐㅑㅒㅓㅔㅕㅖㅣ"); HORIZ = set("ㅗㅛㅜㅠㅡ")        # 나머지(ㅘㅙㅚㅝㅞㅟㅢ)는 섞인 모음
V_SPLIT = {"ㅐ": "ㅏㅣ", "ㅒ": "ㅑㅣ", "ㅔ": "ㅓㅣ", "ㅖ": "ㅕㅣ"}                     # 세로 모음 + ㅣ
MIXED = {"ㅘ": ("ㅗ", "ㅏ"), "ㅙ": ("ㅗ", "ㅏㅣ"), "ㅚ": ("ㅗ", "ㅣ"), "ㅝ": ("ㅜ", "ㅓ"), "ㅞ": ("ㅜ", "ㅓㅣ"), "ㅟ": ("ㅜ", "ㅣ"), "ㅢ": ("ㅡ", "ㅣ")}

# 글씨 상자(폰트 단위): 실제로 쓴 글자(fit_syllable 결과)와 같은 크기로 맞춘다
BOXW, BOXH, CX, CY = 720, 700, 500, 330
CAN_W, CAN_H, CAN_X0, CAN_YTOP = 1200, 1200, 100, 900          # 캔버스: x -100..1100, y -300..900 (1px = 1단위)
STRETCH = 1.9                                                   # 부품을 자리에 맞추려고 한쪽만 늘리는 최대 배율
STRETCH_PART = {"ㅇ": 1.15, "ㅁ": 1.25}                          # 동그라미·네모는 찌그러지면 어색해서 따로 제한
PAD = 16

# 자리(상자 안 비율, y는 위쪽이 1): (x0, y0, x1, y1)
SLOTS = {
    (False, "vert"):  {"L": (0.00, 0.00, 0.52, 1.00), "V": (0.58, 0.00, 1.00, 1.00)},
    (False, "horiz"): {"L": (0.00, 0.52, 1.00, 1.00), "V": (0.00, 0.00, 1.00, 0.42)},
    (False, "mixed"): {"L": (0.00, 0.52, 0.55, 1.00), "Vh": (0.00, 0.00, 0.60, 0.46), "Vv": (0.66, 0.00, 1.00, 1.00)},
    (True, "vert"):   {"L": (0.00, 0.40, 0.50, 1.00), "V": (0.56, 0.40, 1.00, 1.00), "T": (0.05, 0.00, 0.95, 0.34)},
    (True, "horiz"):  {"L": (0.00, 0.64, 1.00, 1.00), "V": (0.00, 0.35, 1.00, 0.60), "T": (0.05, 0.00, 0.95, 0.31)},
    (True, "mixed"):  {"L": (0.00, 0.66, 0.55, 1.00), "Vh": (0.00, 0.40, 0.60, 0.62), "Vv": (0.66, 0.40, 1.00, 1.00), "T": (0.05, 0.00, 0.95, 0.34)},
}

def decompose(ch):
    s = ord(ch) - 0xAC00
    return L_LIST[s // 588], V_LIST[(s % 588) // 28], T_LIST[s % 28]

def load_parts(cells_dir):
    """자음·모음 부품(1쪽 jamo 칸)을 읽어 글씨 부분만 잘라 둔다. 같은 글자가 여러 쪽에 있으면 나중 쪽을 쓴다."""
    page_no = lambda p: int(re.search(r"p(\d+)_cells", os.path.basename(p)).group(1))
    parts = {}
    for jf in sorted(glob.glob(os.path.join(cells_dir, "p*_cells.json")), key=page_no):
        for m in json.load(open(jf)):
            if m["kind"] != "jamo": continue
            big = bf.prep_mask(os.path.join(cells_dir, m["file"]))
            if big is None: continue
            x, y, w, h = cv2.boundingRect(big)
            crop = np.pad(big[y:y+h, x:x+w], PAD)
            parts[m["char"]] = {"mask": crop, "w0": bf.stroke_w(crop), "ink": (w, h)}
    return parts

def hsplit(slot, fracs):
    """자리를 가로로 나눈다(부품 여러 개를 나란히 놓을 때). fracs=각 부품의 폭 비율."""
    x0, y0, x1, y1 = slot; tot = sum(fracs) + 0.08 * (len(fracs) - 1); out = []; cur = x0
    for f in fracs:
        w = (x1 - x0) * f / tot; out.append((cur, y0, cur + w, y1)); cur += w + (x1 - x0) * 0.08 / tot
    return out

def to_units(slot):
    x0, y0, x1, y1 = slot; bx, by = CX - BOXW / 2, CY - BOXH / 2
    return bx + x0 * BOXW, by + y0 * BOXH, bx + x1 * BOXW, by + y1 * BOXH

def place(canvas, part, slot, target, name=""):
    ux0, uy0, ux1, uy1 = to_units(slot); sw, sh = ux1 - ux0, uy1 - uy0
    iw, ih = part["ink"]; nw, nh = iw * bf.UPK, ih * bf.UPK            # 부품의 원래 크기(폰트 단위)
    kx0, ky0 = sw / nw, sh / nh; k = min(kx0, ky0)
    st = STRETCH_PART.get(name, STRETCH)
    kx, ky = (min(kx0, k * st), k) if kx0 >= ky0 else (k, min(ky0, k * st))
    r = int(round((target / (np.sqrt(kx * ky) * bf.UPK) - part["w0"]) / 2)); r = max(bf.EQ_R_MIN, min(bf.EQ_R_MAX, r))
    m = bf.offset_mask(part["mask"], r)                                  # 굵기 맞춤: 최종 크기에서 목표 굵기가 되도록 깎기/부풀리기
    g = cv2.GaussianBlur(m, (0, 0), 1.2)
    ow, oh = max(2, int(round(m.shape[1] * bf.UPK * kx))), max(2, int(round(m.shape[0] * bf.UPK * ky)))
    g = cv2.resize(g, (ow, oh), interpolation=cv2.INTER_AREA)
    cx, cy = (ux0 + ux1) / 2 + CAN_X0, CAN_YTOP - (uy0 + uy1) / 2     # 자리 중심(캔버스 좌표)
    x0, y0 = int(round(cx - ow / 2)), int(round(cy - oh / 2))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(CAN_W, x0 + ow), min(CAN_H, y0 + oh)
    if xb > xa and yb > ya:
        canvas[ya:yb, xa:xb] = np.maximum(canvas[ya:yb, xa:xb], g[ya - y0:yb - y0, xa - x0:xb - x0])

def compose_canvas(ch, parts, target):
    L, V, T = decompose(ch)
    vtype = "vert" if V in VERT else "horiz" if V in HORIZ else "mixed"
    S = SLOTS[(bool(T), vtype)]
    canvas = np.zeros((CAN_H, CAN_W), np.float32)
    def put(names, slot):
        for nm, sl in zip(names, hsplit(slot, [1.0] * len(names))): place(canvas, parts[nm], sl, target, nm)
    put(DOUBLE.get(L, L), S["L"])
    if vtype == "vert":
        names = V_SPLIT.get(V, V)
        if len(names) == 1: put(names, S["V"])
        else:
            for nm, sl in zip(names, hsplit(S["V"], [0.62, 0.30])): place(canvas, parts[nm], sl, target, nm)
    elif vtype == "horiz": put(V, S["V"])
    else:
        h, v = MIXED[V]; put(h, S["Vh"])
        if len(v) == 1: put(v, S["Vv"])
        else:
            for nm, sl in zip(v, hsplit(S["Vv"], [0.62, 0.30])): place(canvas, parts[nm], sl, target, nm)
    if T: put(COMP_T.get(T, T), S["T"])
    return canvas

def canvas_to_contours(canvas):
    """캔버스 -> 글자 윤곽(폰트 좌표). build_font 와 같은 윤곽 따기."""
    mask = (canvas > 110).astype(np.uint8) * 255
    if (mask > 0).sum() < 3: return None
    import potrace
    pl = potrace.Bitmap(255 - mask).trace(turdsize=3, alphamax=1.1, opticurve=True, opttolerance=0.3)
    conv = lambda p: (p.x - CAN_X0, CAN_YTOP - p.y)
    out = []
    for curve in pl:
        segs = [("M", conv(curve.start_point))]
        for s in curve.segments:
            if s.is_corner: segs += [("L", conv(s.c)), ("L", conv(s.end_point))]
            else: segs.append(("C", conv(s.c1), conv(s.c2), conv(s.end_point)))
        out.append(segs)
    return out or None

if __name__ == "__main__":
    from PIL import Image, ImageDraw, ImageFont
    cells_dir, outdir = sys.argv[1], sys.argv[2]; target = float(sys.argv[3]) if len(sys.argv) > 3 else 46.0
    os.makedirs(outdir, exist_ok=True); parts = load_parts(cells_dir)
    print("부품:", "".join(sorted(parts)), len(parts), "개")
    font_path = os.environ.get("REAL_FONT")
    f = ImageFont.truetype(font_path, 1000) if font_path else None
    calib = os.environ.get("CALIB", "한글좋밥꿈왜의읽있안녕했괜찮")
    cell = 230; imgs = []
    for ch in calib:
        comp = (np.clip(compose_canvas(ch, parts, target), 0, 255) > 110).astype(np.uint8) * 255
        real = Image.new("L", (CAN_W, CAN_H), 0)
        if f: ImageDraw.Draw(real).text((CAN_X0, CAN_YTOP), ch, font=f, fill=255, anchor="ls")
        tile = np.zeros((2 * cell, cell), np.uint8)
        for i, a in enumerate((np.array(real), comp)):
            crop = a[150:1050, 100:1100]; tile[i*cell:(i+1)*cell, :] = cv2.resize(crop, (cell, cell), interpolation=cv2.INTER_AREA)
        imgs.append(255 - tile)
    cols = 7; rows = (len(imgs) + cols - 1) // cols
    sheet = np.full((rows * 2 * cell + 10, cols * cell + 10), 255, np.uint8)
    for i, t in enumerate(imgs):
        r, c = divmod(i, cols); sheet[5 + r*2*cell:5 + (r+1)*2*cell, 5 + c*cell:5 + (c+1)*cell] = t
        cv2.rectangle(sheet, (5 + c*cell, 5 + r*2*cell), (5 + (c+1)*cell - 1, 5 + (r+1)*2*cell - 1), 170, 1)
        cv2.line(sheet, (5 + c*cell, 5 + r*2*cell + cell), (5 + (c+1)*cell - 1, 5 + r*2*cell + cell), 200, 1)
    cv2.imwrite(os.path.join(outdir, "calib.png"), sheet); print("저장:", os.path.join(outdir, "calib.png"), "| 순서:", calib, "(칸마다 위=진짜 손글씨, 아래=조합)")
