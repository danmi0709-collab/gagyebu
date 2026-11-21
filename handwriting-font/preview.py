"""폰트로 카톡 말풍선 모양 미리보기 PNG 만들기. 사용: python3 -I preview.py <폰트.ttf> <출력.png> [문장들...]"""
import sys
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

def main(ttf, out, lines):
    cmap = TTFont(ttf).getBestCmap()
    missing = sorted({c for l in lines for c in l if c != " " and ord(c) not in cmap})
    if missing: print("폰트에 없는 글자(건너뜀 아님, 기본 글꼴로 대체될 글자):", "".join(missing))
    f = ImageFont.truetype(ttf, 64)
    W = 1000; img = Image.new("RGB", (W, 150 * len(lines) + 60), "#b9cde0"); d = ImageDraw.Draw(img)
    y = 40
    for i, t in enumerate(lines):
        l, tp, r, b = d.textbbox((0, 0), t, font=f)
        w, h = r - l, b - tp
        right = i % 2 == 1                       # 짝수 줄은 상대, 홀수 줄은 나
        bw, bh = w + 70, 112
        x = W - 40 - bw if right else 40
        d.rounded_rectangle((x, y, x + bw, y + bh), 28, fill="#fee500" if right else "#ffffff")
        d.text((x + 35 - l, y + (bh - h) / 2 - tp), t, font=f, fill="#111111")
        y += 150
    img.save(out); print("미리보기 저장:", out)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
