import subprocess
# Video alani (ekran goruntusu icinde): x,y,w,h
VX, VY, VW, VH = 16, 70, 888, 500
noktalar = {
    "gokyuzu": (0.50, 0.08), "kule_parlak": (0.68, 0.15),
    "yuz": (0.47, 0.40), "sac": (0.53, 0.32),
    "ust_siyah": (0.47, 0.47), "controller": (0.20, 0.90),
    "hud_camgobegi": (0.05, 0.25), "magenta_serit": (0.75, 0.12),
    "sol_bina": (0.10, 0.30), "sag_bina": (0.90, 0.40),
    "zemin_karanlik": (0.47, 0.62), "jog": (0.13, 0.85),
}
for ad, (fx, fy) in noktalar.items():
    x, y = VX + int(VW * fx), VY + int(VH * fy)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error",
                        "-i", ".scratchpad/ref5_play.png",
                        "-vf", f"crop=12:12:{x}:{y}",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True)
    d = r.stdout
    n = len(d) // 3
    R = sum(d[i] for i in range(0, len(d), 3)) // n
    G = sum(d[i] for i in range(1, len(d), 3)) // n
    B = sum(d[i] for i in range(2, len(d), 3)) // n
    print(f"{ad:14s} #%02X%02X%02X  (R{R} G{G} B{B})" % (R, G, B))
