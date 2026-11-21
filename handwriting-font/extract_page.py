"""사진 한 장 -> 똑바로 펴기 -> 칸별 잉크 이미지(PNG).
사용: python3 -I extract_page.py <사진> <쪽번호> <출력폴더> [임계값=0.9]"""
import sys, os, json
import numpy as np, cv2

S = 10  # 1mm = 10px
HERE = os.path.dirname(os.path.abspath(__file__))

def rectify(img, layout, page):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50),
                                  cv2.aruco.DetectorParameters())
    want = layout["pages"][page-1]["marker_ids"]
    for g in (gray, cv2.createCLAHE(3.0, (8, 8)).apply(gray)):
        corners, ids, _ = det.detectMarkers(g)
        if ids is not None and len(set(ids.flatten()) & set(want)) >= 3:      # 3개만 있어도 사진을 펼 수 있다(1개는 가려져도 됨)
            break
    else:
        found = None if ids is None else sorted(ids.flatten().tolist())
        sys.exit(f"표식을 3개 이상 못 찾았어요. 찾은 것: {found}, 필요한 것: {want}")
    n_found = len(set(ids.flatten()) & set(want))
    if n_found < 4: print(f"참고: 표식 {n_found}개로 펴요(가려진 표식이 있어요)")
    m = layout["marker_size_mm"]; src, dst = [], []
    for cs, i in zip(corners, ids.flatten()):
        if i in want:
            mx, my = layout["markers_mm"][want.index(i)]
            for p, q in zip(cs.reshape(4, 2), [(mx, my), (mx+m, my), (mx+m, my+m), (mx, my+m)]):
                src.append(p); dst.append([q[0]*S, q[1]*S])
    H, _ = cv2.findHomography(np.float32(src), np.float32(dst), cv2.RANSAC, 5.0)
    W, Hh = layout["paper_mm"]
    return cv2.warpPerspective(img, H, (int(W*S), int(Hh*S)), flags=cv2.INTER_CUBIC)

def ink_norm(warped):
    g = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY).astype(np.float32)
    bg = cv2.morphologyEx(g, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (45, 45)))
    bg = cv2.GaussianBlur(bg, (0, 0), 15)
    return np.clip(g / np.maximum(bg, 1), 0, 1.2)   # 종이=1, 잉크는 0에 가까움

FLOOR = 0.42    # 안내선 구역이라도 이보다 진하면 무조건 글씨
GHW = 6         # 안내선 구역 반폭(px)
SEARCH = 8      # 선 위치를 계산값 근처 ±8px에서 실제로 찾는다(종이 휨 대비)
MARGIN_LINE = 0.15   # 선보다 이만큼 더 진해야 글씨로 본다

def refine(crop, o, p, a, b):
    """계산된 선 위치 p 근처에서 실제로 가장 선처럼 어두운 줄을 찾아 위치를 바로잡는다."""
    vals = []
    for d in range(-SEARCH, SEARCH + 1):
        q = p + d
        seg = None
        if o == "h" and 0 <= q < crop.shape[0]: seg = crop[q, a:b]
        if o == "v" and 0 <= q < crop.shape[1]: seg = crop[a:b, q]
        vals.append(float(np.percentile(seg, 30)) if seg is not None and seg.size else 9.0)
    d = int(np.argmin(vals))
    return p + d - SEARCH if vals[d] < vals[SEARCH] - 0.03 else p

def threshold_map(crop, kind, bw, bh, marg, layout, thr):
    """칸 조각의 픽셀별 '글씨 판정 기준값'. 안내선 구역은 그 선의 실제 진하기를 재서 선보다 진한 것만 글씨로 본다.
    반환: (기준값 지도, 안내선 구역 표시)"""
    T = np.full(crop.shape, thr, np.float32); G = np.zeros(crop.shape, bool)
    x0, y0, x1, y1 = marg, marg, marg + bw, marg + bh
    lines = [("h", y0, x0, x1), ("h", y1, x0, x1), ("v", x0, y0, y1), ("v", x1, y0, y1)]       # 칸 테두리
    if kind == "latin":
        B = layout["box_mm"] * S; base = layout["baseline_from_top_mm"] * S
        lines += [("h", int(y0 + t), x0, x1) for t in (base, B * 0.10, base - B * 0.32)]     # 바닥선, 대문자선, 소문자선
    else:
        lines += [("v", x0 + bw // 2, y0, y1), ("h", y0 + bh // 2, x0, x1)]                   # 십자선
    for o, p, a, b in lines:
        p = refine(crop, o, p, a, b)
        dim = crop.shape[0] if o == "h" else crop.shape[1]
        lo, hi = max(0, p - GHW), min(dim, p + GHW + 1)       # 칸 조각 밖으로 나가지 않게
        if hi <= lo: continue
        sl = (slice(lo, hi), slice(a, b)) if o == "h" else (slice(a, b), slice(lo, hi))
        band = crop[sl] if o == "h" else crop[sl].T
        E = 15                                                       # 선 양쪽 끝 1.5mm: 손글씨가 거의 안 오는 구간
        ends = np.concatenate([band[:, :E], band[:, -E:]], axis=1) if band.shape[1] > 3 * E else band
        level = float(np.percentile(ends, 30, axis=1).min())         # 이 선 자체의 진하기
        m = MARGIN_LINE if level < 0.8 else 0.07                     # 선이 아주 흐린 곳은 여유를 줄여 연한 글씨를 살린다
        t_line = max(FLOOR, min(thr, level - m))
        T[sl] = np.minimum(T[sl], t_line); G[sl] = True
    return T, G

def main(photo, page, outdir, thr=0.9):
    layout = json.load(open(os.path.join(HERE, "layout.json")))
    img = cv2.imread(photo)
    assert img is not None, "사진을 못 읽었어요"
    warped = rectify(img, layout, page)
    os.makedirs(outdir, exist_ok=True)
    cv2.imwrite(os.path.join(outdir, f"p{page}_rectified.jpg"), warped)
    norm = ink_norm(warped)
    MARG = int(0.8 * S)
    cells = layout["pages"][page-1]["cells"]; tiles = []
    meta = []
    for c in cells:
        bx, by, bw, bh = [int(round(v*S)) for v in c["box_mm"]]
        crop = norm[by-MARG:by+bh+MARG, bx-MARG:bx+bw+MARG]
        dark = float(np.percentile(crop, 0.3))                       # 이 칸에서 가장 진한 글씨 농도
        thr_c = min(thr, max(0.5, (1.0 + dark) / 2))                 # 종이(1.0)와 가장 진한 글씨의 중간 = 획의 실제 가장자리
        T, G = threshold_map(crop, c["kind"], bw, bh, MARG, layout, thr_c)
        ink = crop < T
        closed = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        ink = (ink | ((closed > 0) & G)).astype(np.uint8) * 255   # 안내선 때문에 끊긴 획 잇기
        # 먼지(작은 알갱이)와 칸 테두리 찌꺼기 제거
        n, lab, st, _ = cv2.connectedComponentsWithStats(ink, 8)
        small = 6 if c["char"] in ".,:;'\"" else 14        # 점으로 쓰는 기호는 작은 알갱이도 글씨
        for k in range(1, n):
            area, hh, ww = st[k, cv2.CC_STAT_AREA], st[k, cv2.CC_STAT_HEIGHT], st[k, cv2.CC_STAT_WIDTH]
            lx, ty = st[k, cv2.CC_STAT_LEFT], st[k, cv2.CC_STAT_TOP]
            mk = lab == k
            # 칸 테두리 0.4mm 이내에만 완전히 붙어 있는 조각 = 테두리 선 찌꺼기
            edge = (ty + hh <= MARG + 4) or (ty >= MARG + bh - 4) or (lx + ww <= MARG + 4) or (lx >= MARG + bw - 4)
            if area < small or edge:
                ink[mk] = 0
        name = f"p{page}_r{c['row']}c{c['col']}_U{ord(c['char']):04X}.png"
        cv2.imwrite(os.path.join(outdir, name), ink)
        meta.append({"char": c["char"], "kind": c["kind"], "file": name, "margin_px": MARG,
                     "ink_px": int((ink > 0).sum())})
        tiles.append(255 - ink)
    json.dump(meta, open(os.path.join(outdir, f"p{page}_cells.json"), "w"), ensure_ascii=False, indent=1)
    h, w = tiles[0].shape
    sheet = np.full((9*h, 8*w), 255, np.uint8)
    for i, t in enumerate(tiles):
        r, col = divmod(i, 8); sheet[r*h:(r+1)*h, col*w:(col+1)*w] = t
        cv2.rectangle(sheet, (col*w, r*h), ((col+1)*w-1, (r+1)*h-1), 160, 1)
    cv2.imwrite(os.path.join(outdir, f"p{page}_contact.png"), cv2.resize(sheet, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
    empty = [m["char"] for m in meta if m["ink_px"] < 150]
    print("칸 수:", len(meta), "| 잉크가 거의 없는 칸:", empty)

if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3], float(sys.argv[4]) if len(sys.argv) > 4 else 0.9)
