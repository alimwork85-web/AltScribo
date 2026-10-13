import math
from PIL import Image, ImageDraw, ImageFilter

S = 1024
SS = 2  # supersample
N = S * SS


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_icon():
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))

    # tile: teal gradient with rounded corners
    grad = Image.new("RGBA", (N, N))
    gd = ImageDraw.Draw(grad)
    top, bot = (16, 104, 122), (8, 56, 70)
    for y in range(N):
        gd.line([(0, y), (N, y)], fill=lerp(top, bot, y / N) + (255,))
    mask = Image.new("L", (N, N), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, N - 1, N - 1], radius=230 * SS, fill=255)
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img)
    k = SS

    # soft shadow for the scroll
    sh = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle([210 * k, 210 * k, 700 * k, 860 * k], radius=70 * k, fill=(0, 0, 0, 110))
    sh = sh.filter(ImageFilter.GaussianBlur(18 * k))
    img.alpha_composite(sh)
    d = ImageDraw.Draw(img)

    cream, cream_dk = (247, 238, 214), (222, 205, 165)
    # scroll roll at bottom (behind) and page
    d.rounded_rectangle([170 * k, 740 * k, 720 * k, 860 * k], radius=60 * k, fill=cream_dk + (255,))
    d.rounded_rectangle([200 * k, 170 * k, 690 * k, 800 * k], radius=62 * k, fill=cream + (255,))
    d.rounded_rectangle([170 * k, 740 * k, 720 * k, 860 * k], radius=60 * k, outline=None, fill=cream_dk + (255,))
    d.rounded_rectangle([196 * k, 756 * k, 694 * k, 790 * k], radius=17 * k, fill=(205, 186, 142, 255))

    # sound-wave bars on the page
    teal = (12, 84, 100)
    cx, cy = 445, 450
    heights = [130, 280, 400, 240, 150]
    for i, h in enumerate(heights):
        x = cx + (i - 2) * 76
        d.rounded_rectangle([(x - 24) * k, (cy - h / 2) * k, (x + 24) * k, (cy + h / 2) * k],
                            radius=24 * k, fill=teal + (255,))

    # quill: lens-shaped feather along an axis
    A, B = (610, 800), (905, 150)
    ax, ay = B[0] - A[0], B[1] - A[1]
    L = math.hypot(ax, ay)
    ux, uy = ax / L, ay / L
    px, py = -uy, ux
    pts_l, pts_r = [], []
    steps = 60
    for i in range(steps + 1):
        t = i / steps
        w = 118 * math.sin(math.pi * t ** 0.85) ** 0.9
        x, y = A[0] + ax * t, A[1] + ay * t
        pts_l.append(((x + px * w) * k, (y + py * w) * k))
        pts_r.append(((x - px * w * 0.8) * k, (y - py * w * 0.8) * k))
    feather = pts_l + pts_r[::-1]
    d.polygon(feather, fill=(222, 130, 42, 255))
    # lighter half of the vane
    half = pts_l + [((A[0] + ax * (i / steps)) * k, (A[1] + ay * (i / steps)) * k) for i in range(steps, -1, -1)]
    d.polygon(half, fill=(238, 160, 66, 255))
    # spine
    tail = (A[0] - ux * 70, A[1] - uy * 70)
    d.line([tail[0] * k, tail[1] * k, (B[0] - ux * 20) * k, (B[1] - uy * 20) * k],
           fill=(120, 60, 16, 255), width=14 * k)
    # nib
    d.polygon([((tail[0] + px * 14) * k, (tail[1] + py * 14) * k),
               ((tail[0] - px * 14) * k, (tail[1] - py * 14) * k),
               ((tail[0] - ux * 60) * k, (tail[1] - uy * 60) * k)], fill=(60, 30, 8, 255))

    return img.resize((S, S), Image.LANCZOS)


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "design/icon_new_1024.png"
    draw_icon().save(out)
