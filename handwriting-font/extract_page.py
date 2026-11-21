"""사진 한 장 -> 똑바로 펴기 -> 칸별 잉크 이미지(PNG).
사용: python3 -I extract_page.py <사진> <쪽번호> <출력폴더> [임계값=0.5]"""
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
        if ids is not None and len(set(ids.flatten()) & set(want)) == 4:
            break
    else:
        found = None if ids is None else sorted(ids.flatten().tolist())
        sys.exit(f"표식 4개를 못 찾았어요. 찾은 것: {found}, 필요한 것: {want}")
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

def main(photo, page, outdir, thr=0.5):
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
        ink = (crop < thr).astype(np.uint8) * 255
        # 아주 작은 먼지 제거
        n, lab, st, _ = cv2.connectedComponentsWithStats(ink, 8)
        for k in range(1, n):
            if st[k, cv2.CC_STAT_AREA] < 6: ink[lab == k] = 0
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
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3], float(sys.argv[4]) if len(sys.argv) > 4 else 0.5)
