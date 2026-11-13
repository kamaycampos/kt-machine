"""Stills that feel filmed: the subject and the room move at different speeds (depth), the light
breathes, dust drifts, the camera has a hand. And the brain forms out of particles."""
import sys, os, subprocess, numpy as np, cv2
S, D = sys.argv[1], sys.argv[2]
FF = os.path.expanduser("~/Kamay/bin/ffmpeg")
W, H, FPS = 1920, 1080, 30
rng = np.random.default_rng(7)

def writer(path):
    return subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
                             "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)

def zoomed(img, s, dx=0.0, dy=0.0, border=cv2.BORDER_REPLICATE):
    M = np.float32([[s, 0, (1 - s) * W / 2 + dx], [0, s, (1 - s) * H / 2 + dy]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=border)

def dust(n=70):
    return [dict(x=rng.uniform(0, W), y=rng.uniform(0, H), r=rng.uniform(1.2, 3.6), a=rng.uniform(0.10, 0.34),
                 vx=rng.uniform(-6, 6), vy=rng.uniform(-14, -3), ph=rng.uniform(0, 6.28)) for _ in range(n)]

def add_dust(frame, parts, t, tint=(170, 215, 255)):
    lay = np.zeros((H, W), np.float32)
    for p in parts:
        x = (p["x"] + p["vx"] * t + 14 * np.sin(p["ph"] + t * 0.8)) % W
        y = (p["y"] + p["vy"] * t) % H
        cv2.circle(lay, (int(x), int(y)), int(round(p["r"])), float(p["a"] * (0.6 + 0.4 * np.sin(p["ph"] + t * 2.1))), -1, cv2.LINE_AA)
    lay = cv2.GaussianBlur(lay, (0, 0), 2.2)
    return np.clip(frame.astype(np.float32) + lay[..., None] * np.float32(tint), 0, 255).astype(np.uint8)

VIG = None
def vignette(frame, k=0.30):
    global VIG
    if VIG is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        VIG = (1 - k * np.clip(r - 0.55, 0, 1) ** 1.6)[..., None]
    return (frame.astype(np.float32) * VIG).astype(np.uint8)

def depth_scene(name, secs=8.0, bg_z=(1.02, 1.07), fg_z=(1.02, 1.13), pan=(0, 0), dusty=True):
    img = cv2.resize(cv2.imread(f"{D}/{name}.jpg"), (W, H), interpolation=cv2.INTER_LANCZOS4)
    fg = cv2.resize(cv2.imread(f"{S}/sc/fg_{name}.png", cv2.IMREAD_UNCHANGED), (W, H), interpolation=cv2.INTER_LANCZOS4)
    alpha = fg[..., 3]
    hole = cv2.dilate((alpha > 30).astype(np.uint8) * 255, np.ones((31, 31), np.uint8))
    small = cv2.resize(img, (W // 4, H // 4)); hs = cv2.resize(hole, (W // 4, H // 4))
    bg = cv2.resize(cv2.inpaint(small, hs, 7, cv2.INPAINT_TELEA), (W, H), interpolation=cv2.INTER_CUBIC)
    keep = cv2.GaussianBlur((hole == 0).astype(np.float32), (0, 0), 9)[..., None]
    bg = (img * keep + bg * (1 - keep)).astype(np.uint8)             # the real picture wherever nothing stood
    a_soft = cv2.GaussianBlur(alpha.astype(np.float32) / 255, (0, 0), 1.4)
    fgc = np.dstack([img, (a_soft * 255).astype(np.uint8)])
    parts, w = dust(), writer(f"{S}/sc/m_{name}.mp4")
    N = int(secs * FPS)
    flick = cv2.GaussianBlur(rng.normal(0, 1, (N + 60, 1)).astype(np.float32), (1, 0), 0, sigmaY=6).ravel() if False else np.convolve(rng.normal(0, 1, N + 60), np.ones(14) / 14, "same")
    for i in range(N):
        t, k = i / FPS, i / (N - 1)
        e = k * k * (3 - 2 * k) * 0.35 + k * 0.65                    # nearly linear, soft at both ends
        hx, hy = 3.0 * np.sin(t * 0.9) + 1.6 * np.sin(t * 2.3 + 1), 2.2 * np.sin(t * 1.1 + 2) + 1.2 * np.sin(t * 2.9)
        b = zoomed(bg, bg_z[0] + (bg_z[1] - bg_z[0]) * e, hx * 0.5 + pan[0] * e * 0.5, hy * 0.5 + pan[1] * e * 0.5)
        f = zoomed(fgc, fg_z[0] + (fg_z[1] - fg_z[0]) * e, hx + pan[0] * e, hy + pan[1] * e, border=cv2.BORDER_CONSTANT)
        a = f[..., 3:4].astype(np.float32) / 255
        fr = (b * (1 - a) + f[..., :3] * a)
        fr = np.clip(fr * (1 + 0.018 * flick[i + 20]), 0, 255).astype(np.uint8)
        if dusty:
            fr = add_dust(fr, parts, t)
        w.stdin.write(vignette(fr).tobytes())
    w.stdin.close(); w.wait(); print("scene", name)

def brain(secs=8.0):
    src = cv2.resize(cv2.imread(f"{D}/b_brain.jpg"), (W, H), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    canvas = np.zeros_like(src)
    sm = cv2.resize(src, (int(W * 0.86), int(H * 0.86)), interpolation=cv2.INTER_AREA)
    y0, x0 = (H - sm.shape[0]) // 2 - 40, (W - sm.shape[1]) // 2
    canvas[y0:y0 + sm.shape[0], x0:x0 + sm.shape[1]] = sm
    lum = canvas.max(axis=2) / 255.0
    noise = cv2.GaussianBlur(rng.uniform(0, 1, (H, W)).astype(np.float32), (0, 0), 0.8)
    fine = rng.uniform(0, 1, (H, W)).astype(np.float32)
    w, N = writer(f"{S}/sc/m_b_brain.mp4"), int(secs * FPS)
    for i in range(N):
        t = i / FPS
        form = min(1.0, t / 1.1)                                        # it gathers out of points of light
        thr = 1.0 - form ** 0.8
        m = np.clip((fine * 0.6 + noise * 0.4 + lum * 0.55 - thr) * 6.0, 0, 1) if form < 1 else 1.0
        fr = canvas * (m[..., None] if form < 1 else 1.0) * (0.35 + 0.65 * form)
        glow = cv2.GaussianBlur(fr, (0, 0), 26) * (0.55 * form + 0.12 * np.sin(t * 2.4))
        spark = (rng.uniform(0, 1, (H, W)) > 0.9993).astype(np.float32) * (lum > 0.08) * 255
        fr = fr + glow + cv2.GaussianBlur(spark, (0, 0), 1.2)[..., None] * np.float32([0.5, 0.8, 1.0]) * (0.6 + 0.4 * np.sin(t * 5))
        out = zoomed(np.clip(fr, 0, 255).astype(np.uint8), 1.0 + 0.06 * t / secs, border=cv2.BORDER_CONSTANT)
        w.stdin.write(out.tobytes())
    w.stdin.close(); w.wait(); print("scene brain")

depth_scene("a_ballroom", fg_z=(1.02, 1.14), bg_z=(1.02, 1.07))
depth_scene("c_mentor", fg_z=(1.03, 1.13), bg_z=(1.02, 1.06), pan=(-26, 0))
depth_scene("d_book", fg_z=(1.04, 1.12), bg_z=(1.03, 1.08), pan=(30, 0))
depth_scene("e_office", fg_z=(1.02, 1.10), bg_z=(1.02, 1.07), pan=(18, 0), dusty=True)
brain()
