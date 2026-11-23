"""위치별 조각(두솔 양식)으로 한글 글자를 조합한다. 모든 칸이 같은 글자 틀 안에 있어서, 부품 3개의 잉크를 그냥 겹치면 된다.
사용: python3 -I compose_tpl.py <tpl폴더> <출력폴더> <페이지번호(가상칸용)> [글자들|all]
 - tpl폴더: out/tpl (pgN_*/tN_cells.json 이 들어 있는 곳)
 - 출력폴더에 p<번호>_cells.json 과 칸 PNG를 만든다(build_font.py 가 진짜 칸처럼 읽는다)."""
import sys, os, json, glob, re
import numpy as np, cv2

CONS = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"; VOW = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
FIN = "ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"
L_LIST = CONS; V_LIST = VOW; T_LIST = [""] + list(FIN)
VERT = set("ㅏㅐㅑㅒㅓㅔㅕㅖㅣ"); HORIZ = set("ㅗㅛㅜㅠㅡ")
# 양식 쪽(PDF 쪽번호)별 칸 내용(왼쪽 위부터 가로로): ('L',자음,'sero|garo|mix',받침있음) / ('V',모음,받침있음) / ('T',받침)
LAYOUT = {
    2: [("L", c, "sero", False) for c in CONS] + [("L", c, "garo", False) for c in CONS] + [("L", c, "mix", False) for c in "ㄱㄲㄴㄷ"],
    3: [("L", c, "mix", False) for c in "ㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"] + [("L", c, "sero", True) for c in CONS] + [("L", c, "garo", True) for c in "ㄱㄲㄴㄷㄸㄹㅁㅂ"],
    4: [("L", c, "garo", True) for c in "ㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"] + [("L", c, "mix", True) for c in CONS] + [("V", v, False) for v in VOW[:12]],
    5: [("V", v, False) for v in VOW[12:]] + [("V", v, True) for v in VOW] + [("T", t) for t in FIN[:12]],
    6: [("T", t) for t in FIN[12:]],
}

def vclass(v): return "sero" if v in VERT else "garo" if v in HORIZ else "mix"

def load_parts(tpl_root):
    """부품 사전: 키 -> (잉크 마스크(칸 좌표), 칸 크기). 같은 키가 있으면 나중 것 사용."""
    parts = {}
    for d in sorted(glob.glob(os.path.join(tpl_root, "pg*"))):
        for jf in glob.glob(os.path.join(d, "t*_cells.json")):
            page = int(re.search(r"t(\d+)_cells", os.path.basename(jf)).group(1))
            if page not in LAYOUT: continue
            meta = json.load(open(jf))
            if len(meta) != len(LAYOUT[page]): print(f"경고: {d} 칸 수 {len(meta)} != 기대 {len(LAYOUT[page])}"); continue
            for m, key in zip(meta, LAYOUT[page]):
                ink = cv2.imread(os.path.join(d, m["file"]), 0)
                x, y, w, h = m["cell"]; ins = m["inset"]
                full = np.zeros((h, w), np.uint8); full[ins:ins + ink.shape[0], ins:ins + ink.shape[1]] = ink[:h - ins, :w - ins]
                parts[key] = (full, (w, h))
    return parts

def parts_for(ch, parts):
    L, V, T = L_LIST[(ord(ch) - 0xAC00) // 588], V_LIST[((ord(ch) - 0xAC00) % 588) // 28], T_LIST[(ord(ch) - 0xAC00) % 28]
    keys = [("L", L, vclass(V), bool(T)), ("V", V, bool(T))] + ([("T", T)] if T else [])
    return keys if all(k in parts for k in keys) else None

def separate_final(V, T, gap=4, max_shrink=0.7):
    """받침 T 가 모음 V 와 세로로 겹치면 아래로 내리고, 칸 아래가 모자라면 받침 높이를 최대 30%까지 줄인다."""
    h, w = V.shape; vy = np.nonzero(V.any(1))[0]; ty = np.nonzero(T.any(1))[0]
    if len(vy) == 0 or len(ty) == 0: return T
    overlap = vy.max() - ty.min() + gap                          # 받침 윗끝이 모음 아랫끝보다 위로 올라간 만큼
    if overlap <= 0: return T
    room = (h - 4) - ty.max()                                    # 칸 아래로 더 내릴 수 있는 여유
    dy = min(overlap, max(room, 0)); rest = overlap - dy
    th = ty.max() - ty.min() + 1; k = max(max_shrink, (th - rest) / th) if rest > 0 else 1.0
    M = np.float32([[1, 0, 0], [0, k, (ty.max() + dy) - k * ty.max()]])          # 받침 아랫끝 기준으로 줄이고 dy 만큼 내림
    return cv2.warpAffine(T, M, (w, h), flags=cv2.INTER_LINEAR)

def compose_cell(ch, parts, box=210, margin=8):
    keys = parts_for(ch, parts)
    if keys is None: return None
    w, h = parts[keys[0]][1]; u = np.zeros((h, w), np.uint8)
    arrs = [parts[k][0][:h, :w] if parts[k][0].shape == (h, w) else cv2.resize(parts[k][0], (w, h)) for k in keys]
    if len(keys) == 3 and keys[1][1] not in VERT:                 # 모음이 가로형·섞인형이면 모음 위에 받침이 쌓이는 구조 -> 겹치면 받침을 내린다
        arrs[2] = separate_final(arrs[1], arrs[2])
    for a in arrs: u = np.maximum(u, a)
    g = cv2.resize(u.astype(np.float32), (box, box), interpolation=cv2.INTER_AREA)         # 칸 -> 우리 칸 규격(21mm=210px)
    out = np.zeros((box + 2 * margin, box + 2 * margin), np.uint8)
    out[margin:margin + box, margin:margin + box] = (g > 100).astype(np.uint8) * 255
    return out

if __name__ == "__main__":
    tpl_root, outdir, page = sys.argv[1], sys.argv[2], int(sys.argv[3]); chars = sys.argv[4] if len(sys.argv) > 4 else "all"
    os.makedirs(outdir, exist_ok=True); parts = load_parts(tpl_root)
    print("부품 종류:", len(parts), "개 (초성", sum(1 for k in parts if k[0] == "L"), "/ 모음", sum(1 for k in parts if k[0] == "V"), "/ 받침", sum(1 for k in parts if k[0] == "T"), ")")
    todo = [chr(c) for c in range(0xAC00, 0xD7A4)] if chars == "all" else list(dict.fromkeys(chars))
    meta = []; skipped = 0
    for ch in todo:
        cell = compose_cell(ch, parts)
        if cell is None: skipped += 1; continue
        name = f"p{page}_v{ord(ch):04X}.png"; cv2.imwrite(os.path.join(outdir, name), cell)
        meta.append({"char": ch, "kind": "hangul", "file": name, "margin_px": 8, "ink_px": int((cell > 0).sum()), "virtual": True})
    json.dump(meta, open(os.path.join(outdir, f"p{page}_cells.json"), "w"), ensure_ascii=False)
    print(f"조합한 글자 {len(meta)}개, 부품이 모자라 건너뛴 글자 {skipped}개")
