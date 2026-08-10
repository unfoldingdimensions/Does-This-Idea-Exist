import sys, re

def lab_to_rgb(L, a, b):
    """CIELAB (D65) -> sRGB, per CSS Color 4 / WCAG luminance chain."""
    eps = 216 / 24389
    kap = 24389 / 27
    def f_inv(t):
        t3 = t ** 3
        return t3 if t3 > eps else (116 * t - 16) / kap
    fy = (L + 16) / 116
    fx = fy + a / 500
    fz = fy - b / 200
    x = 0.95047 * f_inv(fx)
    y = 1.00000 * f_inv(fy)
    z = 1.08883 * f_inv(fz)
    r = 3.2406 * x - 1.5372 * y - 0.4986 * z
    g = -0.9689 * x + 1.8758 * y + 0.0415 * z
    bl = 0.0557 * x - 0.2040 * y + 1.0570 * z
    def gamma(c):
        c = max(0.0, min(1.0, c))
        return 1.055 * (c ** (1 / 2.4)) - 0.055 if c > 0.0031308 else 12.92 * c
    return tuple(round(gamma(c) * 255) for c in (r, g, bl))

def parse(v):
    v = v.strip().lower()
    m = re.match(r'lab\(([\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)', v)
    if m:
        return lab_to_rgb(*map(float, m.groups()))
    m = re.match(r'rgba?\(([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)', v)
    if m:
        return tuple(int(round(float(x))) for x in m.groups())
    h = v.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def luminance(rgb):
    r, g, b = (x / 255 for x in rgb)
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

def contrast(fg, bg):
    l1, l2 = luminance(parse(fg)), luminance(parse(bg))
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)

if __name__ == "__main__":
    pairs = [
        ("body text / body bg (dark)", "lab(91.97 0.79596 9.22805)", "lab(8.87528 -0.326201 -5.14618)"),
        ("muted text / body bg (dark)", "lab(74.5408 1.53458 9.15563)", "lab(8.87528 -0.326201 -5.14618)"),
        ("button text / button bg (dark)", "lab(8.56326 2.15314 3.86508)", "lab(86.1884 1.066 11.5901)"),
    ]
    for name, fg, bg in pairs:
        print(f"{name}: {contrast(fg, bg):.2f}:1")
