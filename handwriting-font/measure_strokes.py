"""폰트 속 글자들의 획 굵기(폰트 단위, 1000=글자 한 칸)를 직접 재서 편차를 보여준다.
사용: python3 -I measure_strokes.py <폰트.ttf> [자세히]"""
import sys, statistics as st
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

SKIP = set(".,:;'\"")

def stroke_w(mask):
    dt = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    mx = cv2.dilate(dt, np.ones((3, 3), np.float32))
    ridge = (dt >= mx - 1e-6) & (dt > 1.0)
    return 2 * float(np.median(dt[ridge])) if ridge.any() else None

def measure(ttf):
    f = ImageFont.truetype(ttf, 1000); cm = TTFont(ttf).getBestCmap(); out = {}
    for cp in sorted(cm):
        ch = chr(cp)
        if ch == " " or ch in SKIP: continue
        img = Image.new("L", (2000, 2000), 0)
        ImageDraw.Draw(img).text((500, 400), ch, font=f, fill=255)
        w = stroke_w((np.array(img) > 127).astype(np.uint8) * 255)
        if w: out[ch] = w
    return out

if __name__ == "__main__":
    m = measure(sys.argv[1]); v = list(m.values())
    print(f"글자 {len(v)}개 | 획 굵기 중간 {st.median(v):.0f} | 최소 {min(v):.0f} 최대 {max(v):.0f} | 표준편차 {st.pstdev(v):.1f} | 편차/중간 {st.pstdev(v)/st.median(v)*100:.0f}%")
    if len(sys.argv) > 2:
        for ch, w in sorted(m.items(), key=lambda t: t[1]): print(ch, round(w), end=" | ")
        print()
