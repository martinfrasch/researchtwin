"""Generate ResearchTwin Discord app icon, bot icon, and banner."""
from PIL import Image, ImageDraw, ImageFont
import math
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
os.makedirs(OUT_DIR, exist_ok=True)

# Brand colors
BG_DARK = (10, 14, 23)       # #0a0e17
BLUE = (52, 152, 219)        # #3498db
GREEN = (46, 204, 113)       # #2ecc71
WHITE = (224, 224, 224)
MUTED = (136, 153, 170)      # #8899aa


def draw_gradient_text(draw, text, x, y, font, color_start, color_end):
    """Draw text with a horizontal gradient by rendering character by character."""
    bbox = font.getbbox(text)
    total_width = bbox[2] - bbox[0]
    current_x = x
    for i, char in enumerate(text):
        t = i / max(len(text) - 1, 1)
        r = int(color_start[0] + t * (color_end[0] - color_start[0]))
        g = int(color_start[1] + t * (color_end[1] - color_start[1]))
        b = int(color_start[2] + t * (color_end[2] - color_start[2]))
        draw.text((current_x, y), char, fill=(r, g, b), font=font)
        char_bbox = font.getbbox(char)
        current_x += char_bbox[2] - char_bbox[0]


def draw_neural_network(draw, cx, cy, radius, color, node_r=6, alpha_lines=80):
    """Draw a stylized neural network / constellation pattern."""
    # Create node positions in a brain-like pattern
    nodes = []
    # Inner ring (glial layer)
    for i in range(6):
        angle = i * math.pi / 3 + math.pi / 6
        r = radius * 0.35
        nodes.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    # Outer ring (neural layer)
    for i in range(8):
        angle = i * math.pi / 4
        r = radius * 0.7
        nodes.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    # Outermost nodes (connector layer)
    for i in range(5):
        angle = i * math.pi * 2 / 5 + math.pi / 10
        r = radius * 0.92
        nodes.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))

    # Draw connections (edges)
    line_color_blue = (BLUE[0], BLUE[1], BLUE[2], alpha_lines)
    line_color_green = (GREEN[0], GREEN[1], GREEN[2], alpha_lines)
    for i, n1 in enumerate(nodes):
        for j, n2 in enumerate(nodes):
            if j <= i:
                continue
            dist = math.sqrt((n1[0] - n2[0]) ** 2 + (n1[1] - n2[1]) ** 2)
            if dist < radius * 0.65:
                t = i / max(len(nodes) - 1, 1)
                lr = int(BLUE[0] + t * (GREEN[0] - BLUE[0]))
                lg = int(BLUE[1] + t * (GREEN[1] - BLUE[1]))
                lb = int(BLUE[2] + t * (GREEN[2] - BLUE[2]))
                draw.line([n1, n2], fill=(lr, lg, lb, alpha_lines), width=2)

    # Draw nodes
    for i, (nx, ny) in enumerate(nodes):
        t = i / max(len(nodes) - 1, 1)
        nr = int(BLUE[0] + t * (GREEN[0] - BLUE[0]))
        ng = int(BLUE[1] + t * (GREEN[1] - BLUE[1]))
        nb = int(BLUE[2] + t * (GREEN[2] - BLUE[2]))
        # Glow
        for gr in range(node_r + 4, node_r, -1):
            alpha = int(40 * (1 - (gr - node_r) / 4))
            draw.ellipse(
                [nx - gr, ny - gr, nx + gr, ny + gr],
                fill=(nr, ng, nb, alpha),
            )
        # Node
        draw.ellipse(
            [nx - node_r, ny - node_r, nx + node_r, ny + node_r],
            fill=(nr, ng, nb, 255),
        )

    return nodes


def generate_app_icon():
    """Generate the 1024x1024 app icon with R.n monogram + neural network."""
    size = 1024
    img = Image.new("RGBA", (size, size), BG_DARK + (255,))
    draw = ImageDraw.Draw(img, "RGBA")

    # Draw neural network in background
    draw_neural_network(draw, size // 2, size // 2, size // 2 - 40, BLUE, node_r=8, alpha_lines=50)

    # Dark overlay circle for text readability
    center_r = 280
    cx, cy = size // 2, size // 2
    for r in range(center_r + 60, center_r - 1, -1):
        alpha = int(220 * min(1, (center_r + 60 - r) / 60))
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(10, 14, 23, alpha),
        )

    # Draw "R" large
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 320)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 120)
        font_dot = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 180)
    except (OSError, IOError):
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 320)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
            font_dot = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 180)
        except (OSError, IOError):
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_dot = ImageFont.load_default()

    # Position "R.n" centered
    r_bbox = font_large.getbbox("R")
    dot_bbox = font_dot.getbbox(".")
    n_bbox = font_small.getbbox("n")

    total_width = (r_bbox[2] - r_bbox[0]) + (dot_bbox[2] - dot_bbox[0]) + (n_bbox[2] - n_bbox[0]) - 20
    start_x = cx - total_width // 2

    # "R" in gradient blue->green
    r_y = cy - (r_bbox[3] - r_bbox[1]) // 2 - 20
    draw_gradient_text(draw, "R", start_x, r_y, font_large, BLUE, (40, 180, 170))

    # "." in green
    dot_x = start_x + (r_bbox[2] - r_bbox[0]) - 15
    dot_y = r_y + (r_bbox[3] - r_bbox[1]) - (dot_bbox[3] - dot_bbox[1]) + 10
    draw.text((dot_x, dot_y), ".", fill=GREEN, font=font_dot)

    # "n" in green
    n_x = dot_x + (dot_bbox[2] - dot_bbox[0]) - 5
    n_y = r_y + (r_bbox[3] - r_bbox[1]) - (n_bbox[3] - n_bbox[1])
    draw.text((n_x, n_y), "n", fill=GREEN, font=font_small)

    # Save
    img_rgb = Image.new("RGB", (size, size), BG_DARK)
    img_rgb.paste(img, mask=img.split()[3])
    path = os.path.join(OUT_DIR, "app-icon-1024.png")
    img_rgb.save(path, "PNG")
    print(f"Saved {path}")
    return path


def generate_bot_icon():
    """Generate the 1024x1024 bot icon - cleaner version with just the monogram."""
    size = 1024
    img = Image.new("RGBA", (size, size), BG_DARK + (255,))
    draw = ImageDraw.Draw(img, "RGBA")

    cx, cy = size // 2, size // 2

    # Subtle outer ring
    ring_r = 460
    for angle_deg in range(0, 360, 1):
        angle = math.radians(angle_deg)
        t = angle_deg / 360
        r_c = int(BLUE[0] + t * (GREEN[0] - BLUE[0]))
        g_c = int(BLUE[1] + t * (GREEN[1] - BLUE[1]))
        b_c = int(BLUE[2] + t * (GREEN[2] - BLUE[2]))
        x = cx + ring_r * math.cos(angle)
        y = cy + ring_r * math.sin(angle)
        for dr in range(6):
            alpha = int(120 * (1 - dr / 6))
            draw.ellipse(
                [x - 4 - dr, y - 4 - dr, x + 4 + dr, y + 4 + dr],
                fill=(r_c, g_c, b_c, alpha),
            )

    # Small constellation dots around the ring
    for i in range(12):
        angle = i * math.pi / 6
        r = ring_r + 20
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        t = i / 12
        nr = int(BLUE[0] + t * (GREEN[0] - BLUE[0]))
        ng = int(BLUE[1] + t * (GREEN[1] - BLUE[1]))
        nb = int(BLUE[2] + t * (GREEN[2] - BLUE[2]))
        draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(nr, ng, nb, 180))

    # Draw "R.n" monogram
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 360)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 140)
        font_dot = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 200)
    except (OSError, IOError):
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 360)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 140)
            font_dot = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 200)
        except (OSError, IOError):
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_dot = ImageFont.load_default()

    r_bbox = font_large.getbbox("R")
    dot_bbox = font_dot.getbbox(".")
    n_bbox = font_small.getbbox("n")

    total_width = (r_bbox[2] - r_bbox[0]) + (dot_bbox[2] - dot_bbox[0]) + (n_bbox[2] - n_bbox[0]) - 20
    start_x = cx - total_width // 2

    r_y = cy - (r_bbox[3] - r_bbox[1]) // 2 - 20
    draw_gradient_text(draw, "R", start_x, r_y, font_large, BLUE, (40, 180, 170))

    dot_x = start_x + (r_bbox[2] - r_bbox[0]) - 15
    dot_y = r_y + (r_bbox[3] - r_bbox[1]) - (dot_bbox[3] - dot_bbox[1]) + 10
    draw.text((dot_x, dot_y), ".", fill=GREEN, font=font_dot)

    n_x = dot_x + (dot_bbox[2] - dot_bbox[0]) - 5
    n_y = r_y + (r_bbox[3] - r_bbox[1]) - (n_bbox[3] - n_bbox[1])
    draw.text((n_x, n_y), "n", fill=GREEN, font=font_small)

    img_rgb = Image.new("RGB", (size, size), BG_DARK)
    img_rgb.paste(img, mask=img.split()[3])
    path = os.path.join(OUT_DIR, "bot-icon-1024.png")
    img_rgb.save(path, "PNG")
    print(f"Saved {path}")
    return path


def generate_banner():
    """Generate the 680x240 banner."""
    w, h = 680, 240
    img = Image.new("RGBA", (w, h), BG_DARK + (255,))
    draw = ImageDraw.Draw(img, "RGBA")

    # Draw subtle neural network across banner
    nodes = []
    for i in range(20):
        x = 30 + (i % 10) * 65 + (15 if i >= 10 else 0)
        y = 40 + (i // 10) * 160
        nodes.append((x, y))

    for i, n1 in enumerate(nodes):
        for j, n2 in enumerate(nodes):
            if j <= i:
                continue
            dist = math.sqrt((n1[0] - n2[0]) ** 2 + (n1[1] - n2[1]) ** 2)
            if dist < 150:
                t = i / max(len(nodes) - 1, 1)
                lr = int(BLUE[0] + t * (GREEN[0] - BLUE[0]))
                lg = int(BLUE[1] + t * (GREEN[1] - BLUE[1]))
                lb = int(BLUE[2] + t * (GREEN[2] - BLUE[2]))
                draw.line([n1, n2], fill=(lr, lg, lb, 35), width=1)

    for i, (nx, ny) in enumerate(nodes):
        t = i / max(len(nodes) - 1, 1)
        nr = int(BLUE[0] + t * (GREEN[0] - BLUE[0]))
        ng = int(BLUE[1] + t * (GREEN[1] - BLUE[1]))
        nb = int(BLUE[2] + t * (GREEN[2] - BLUE[2]))
        draw.ellipse([nx - 3, ny - 3, nx + 3, ny + 3], fill=(nr, ng, nb, 60))

    # Dark overlay for text
    for x in range(w):
        for y_off in range(h):
            pass  # Skip pixel-level - use rectangle overlay instead

    draw.rectangle([120, 30, 560, 210], fill=(10, 14, 23, 200))

    # Text
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 52)
        font_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        font_tag = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except (OSError, IOError):
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
            font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
            font_tag = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except (OSError, IOError):
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()
            font_tag = ImageFont.load_default()

    # "ResearchTwin" centered
    title = "ResearchTwin"
    title_bbox = font_title.getbbox(title)
    title_w = title_bbox[2] - title_bbox[0]
    title_x = (w - title_w) // 2
    draw_gradient_text(draw, title, title_x, 55, font_title, BLUE, GREEN)

    # Subtitle
    sub = "Federated Agentic Web of Research Knowledge"
    sub_bbox = font_sub.getbbox(sub)
    sub_w = sub_bbox[2] - sub_bbox[0]
    sub_x = (w - sub_w) // 2
    draw.text((sub_x, 120), sub, fill=MUTED, font=font_sub)

    # Tags
    tags = "/research  /sindex  S-index  Digital Twin  RAG"
    tag_bbox = font_tag.getbbox(tags)
    tag_w = tag_bbox[2] - tag_bbox[0]
    tag_x = (w - tag_w) // 2
    draw.text((tag_x, 160), tags, fill=(BLUE[0], BLUE[1], BLUE[2], 150), font=font_tag)

    img_rgb = Image.new("RGB", (w, h), BG_DARK)
    img_rgb.paste(img, mask=img.split()[3])
    path = os.path.join(OUT_DIR, "banner-680x240.png")
    img_rgb.save(path, "PNG")
    print(f"Saved {path}")
    return path


if __name__ == "__main__":
    generate_app_icon()
    generate_bot_icon()
    generate_banner()
    print("Done! Check assets/ directory.")
