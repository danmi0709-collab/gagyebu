"""두솔 템플릿(검은 네모 4개 + 회색 밑그림 + 파란 점선 상자) 사진/스캔 -> 칸별 '조각 하나' 잉크 PNG.
빈 양식을 같은 크기로 겹쳐서 빼므로, 인쇄된 밑그림·상자·테두리는 글씨로 잡히지 않는다.
사용: python3 -I extract_template.py <빈양식.pdf> <PDF쪽번호> <사진> <출력폴더> [라벨.json 키]"""
import sys, os, json, subprocess, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
import extract_page as ep          # ink_norm(종이=1, 잉크는 0에 가깝게)을 재사용

DPI = 254                           # 1mm = 10px (우리 종이와 같은 규격)

def render_blank(pdf, page, outdir):
    base = os.path.join(outdir, f"blank_{page}")
    subprocess.run(["pdftoppm", "-r", str(DPI), "-f", str(page), "-l", str(page), "-png", "-singlefile", pdf, base], check=True)
    return cv2.imread(base + ".png")

def find_squares(img):
    """검은 정사각형 후보들의 (중심, 넓이)"""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); H, W = g.shape
    out = []
    for thr in (70, 100):
        m = (g < thr).astype(np.uint8) * 255
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cs:
            x, y, w, h = cv2.boundingRect(c); a = cv2.contourArea(c)
            if 0.75 < w / h < 1.33 and a / (w * h) > 0.85 and 0.00015 * H * W < a < 0.004 * H * W:
                out.append(((x + w / 2, y + h / 2), a))
        if len(out) >= 4: break
    uniq = []                                                       # 같은 네모를 두 기준에서 중복으로 모은 것 제거
    for c in out:
        if all(np.hypot(c[0][0] - u[0][0], c[0][1] - u[0][1]) > 20 for u in uniq): uniq.append(c)
    return uniq

def order4(pts):
    p = np.array(pts, np.float32); s = p.sum(1); d = p[:, 0] - p[:, 1]
    return np.float32([p[np.argmin(s)], p[np.argmax(d)], p[np.argmax(s)], p[np.argmin(d)]])   # TL,TR,BR,BL

def corner_squares(img, ref_aspect=None):
    cands = find_squares(img)
    if len(cands) < 4: sys.exit(f"검은 네모를 4개 못 찾았어요(찾은 것 {len(cands)}개). 네 모서리가 다 나오게 위에서 똑바로 찍어 주세요.")
    cands = sorted(cands, key=lambda t: -t[1])[:12]; best = None
    for combo in itertools.combinations(cands, 4):
        areas = [c[1] for c in combo]
        if max(areas) / min(areas) > 1.7: continue
        q = order4([c[0] for c in combo]); w = np.linalg.norm(q[1] - q[0]); h = np.linalg.norm(q[3] - q[0])
        if min(w, h) < 50: continue                                  # 점이 겹친 엉터리 조합은 건너뜀
        asp = w / h
        score = abs(np.log(asp / (ref_aspect or 0.707))) + 0.2 * np.log(max(areas) / min(areas))
        if best is None or score < best[0]: best = (score, q)
    if best is None: sys.exit("검은 네모 4개로 이루어진 모서리 조합을 못 찾았어요.")
    return best[1]

def detect_cells(blank):
    g = cv2.cvtColor(blank, cv2.COLOR_BGR2GRAY); hsv = cv2.cvtColor(blank, cv2.COLOR_BGR2HSV)
    m = ((g < 200) & (g > 40) & (hsv[..., 1] < 60)).astype(np.uint8) * 255          # 칸 테두리(진한 회색, 파랑 아님)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE); boxes = []
    for c in cs:
        x, y, w, h = cv2.boundingRect(c)
        if 200 < w < 340 and 200 < h < 340 and 0.9 < w / h < 1.1: boxes.append((x, y, w, h))
    if not boxes: return []
    hh = int(np.median([b[3] for b in boxes])); boxes.sort(key=lambda b: (round(b[1] / (hh * 0.6)), b[0]))
    return boxes

def blue_slot(blank, box):
    x, y, w, h = box; hsv = cv2.cvtColor(blank[y:y+h, x:x+w], cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] > 95) & (hsv[..., 0] < 125) & (hsv[..., 1] > 35) & (hsv[..., 2] > 140)).astype(np.uint8) * 255
    ys, xs = np.nonzero(m)
    if len(xs) < 20: return None
    return [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)]      # 칸 안 상대 좌표

def main(pdf, page, photo, outdir, labels_key=None, labels_file=None):
    os.makedirs(outdir, exist_ok=True)
    blank = render_blank(pdf, page, outdir); H, W = blank.shape[:2]
    bq = corner_squares(blank)                                                       # 빈 양식의 네 모서리 네모 중심
    img = cv2.imread(photo); assert img is not None, "사진을 못 읽었어요"
    asp = np.linalg.norm(bq[1] - bq[0]) / np.linalg.norm(bq[3] - bq[0])
    pq = corner_squares(img, asp)
    M = cv2.getPerspectiveTransform(pq, bq)
    warped = cv2.warpPerspective(img, M, (W, H), flags=cv2.INTER_CUBIC)
    cv2.imwrite(os.path.join(outdir, f"t{page}_rectified.jpg"), warped)
    boxes = detect_cells(blank)
    norm = ep.ink_norm(warped)
    bnorm = ep.ink_norm(blank)                                                       # 빈 양식도 같은 방식으로(종이=1, 밑그림≈0.9, 테두리≈0.5)
    ref = cv2.erode(bnorm, np.ones((9, 9), np.uint8))                                # 인쇄물을 ±4px 부풀려서 사진 속 어긋남을 흡수
    ratio = np.clip(norm / np.clip(ref, 0.3, 1.0), 0, 1.3)                           # 사진에서 인쇄물을 나눠 없앰 -> 손글씨만 남음
    labels = None
    if labels_file and labels_key:
        labels = json.load(open(labels_file)).get(labels_key)
    meta = []; tiles = []
    for i, (x, y, w, h) in enumerate(boxes):
        inset = 5
        crop = ratio[y+inset:y+h-inset, x+inset:x+w-inset]
        dark = float(np.percentile(crop, 0.3)); thr = min(0.85, max(0.5, (1.0 + dark) / 2))
        ink = (crop < thr).astype(np.uint8) * 255
        n, lab, st, _ = cv2.connectedComponentsWithStats(ink, 8)
        for k in range(1, n):
            if st[k, cv2.CC_STAT_AREA] < 14: ink[lab == k] = 0
        r, c = divmod(i, 6) if len(boxes) else (0, 0)
        name = f"t{page}_{i:03d}.png"; cv2.imwrite(os.path.join(outdir, name), ink)
        slot = blue_slot(blank, (x, y, w, h))
        meta.append({"index": i, "label": labels[i] if labels and i < len(labels) else None, "file": name,
                     "cell": [x, y, w, h], "slot_in_cell": slot, "inset": inset, "ink_px": int((ink > 0).sum()), "thr": round(thr, 2)})
        tiles.append(255 - cv2.resize(ink, (150, 150), interpolation=cv2.INTER_AREA))
    json.dump(meta, open(os.path.join(outdir, f"t{page}_cells.json"), "w"), ensure_ascii=False, indent=1)
    cols = 6; rows = (len(tiles) + cols - 1) // cols
    sheet = np.full((rows * 150, cols * 150), 255, np.uint8)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols); sheet[r*150:(r+1)*150, c*150:(c+1)*150] = t
        cv2.rectangle(sheet, (c*150, r*150), ((c+1)*150-1, (r+1)*150-1), 170, 1)
    cv2.imwrite(os.path.join(outdir, f"t{page}_contact.png"), sheet)
    empty = [m["index"] for m in meta if m["ink_px"] < 200]
    print(f"칸 {len(boxes)}개 | 파란 상자 찾은 칸 {sum(1 for m in meta if m['slot_in_cell'])}개 | 잉크가 거의 없는 칸: {empty}")

if __name__ == "__main__":
    a = sys.argv
    main(a[1], int(a[2]), a[3], a[4], a[5] if len(a) > 5 else None, os.path.join(os.path.dirname(os.path.abspath(__file__)), "doosol_labels.json"))
