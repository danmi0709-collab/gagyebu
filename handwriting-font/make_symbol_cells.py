"""기호 양식(28칸)에서 새 기호만 우리 칸 규격(21mm)으로 옮겨 칸 PNG와 p<번호>_cells.json 을 만든다.
사용: python3 -I make_symbol_cells.py <tpl/sym 폴더> <출력폴더> <페이지번호>"""
import sys, os, json
import numpy as np, cv2
ORDER = list("<>^*+=_[]{}|\\`$₩…★☆→←↑↓♪※×÷°")           # 양식의 칸 순서(왼쪽 위부터 가로로)
NEW = set("₩…★☆→←↑↓♪※×÷°")                              # 이미 폰트에 있는 기호는 건드리지 않는다
def main(tpl, outdir, page, box=210, margin=8):
    meta = json.load(open(os.path.join(tpl, "t1_cells.json"))); assert len(meta) == len(ORDER), len(meta)
    os.makedirs(outdir, exist_ok=True); out = []
    for m, ch in zip(meta, ORDER):
        if ch not in NEW: continue
        ink = cv2.imread(os.path.join(tpl, m["file"]), 0); x, y, w, h = m["cell"]; ins = m["inset"]
        full = np.zeros((h, w), np.uint8); full[ins:ins + ink.shape[0], ins:ins + ink.shape[1]] = ink[:h - ins, :w - ins]
        g = cv2.resize(full.astype(np.float32), (box, box), interpolation=cv2.INTER_AREA)
        cell = np.zeros((box + 2 * margin,) * 2, np.uint8); cell[margin:margin + box, margin:margin + box] = (g > 100) * 255
        name = f"p{page}_s{ord(ch):04X}.png"; cv2.imwrite(os.path.join(outdir, name), cell)
        out.append({"char": ch, "kind": "latin", "file": name, "margin_px": margin, "ink_px": int((cell > 0).sum())})
    json.dump(out, open(os.path.join(outdir, f"p{page}_cells.json"), "w"), ensure_ascii=False)
    print("새 기호", len(out), "개:", "".join(o["char"] for o in out))
if __name__ == "__main__": main(sys.argv[1], sys.argv[2], int(sys.argv[3]))
