"""SHOW THE LABEL (WB, 4 Nov 2026 - Kamay: "Yes, build it in").

When Kevin names a product and an ingredient, the product's real ingredient list appears on screen
and the ingredient is highlighted and circled on the word he says it. Proof people can see, and it
gets sent ("look what's in this"). Sample he approved: work/label_sample (Doritos, MSG).

THE LABEL HAS TO BE TRUE. 4 Nov 2026: WB's "Why Kraft cheese is mostly oil" - the US Kraft Singles
label lists no oil. So nothing here is typed by a planner: the ingredient list is fetched from Open
Food Facts by barcode, and if the ingredient to circle is not on it, there is no label (check_plan
refuses the plan; the renderer refuses the card). Set in our own type - never a photo of their pack.

A plan clip opts in:
    "label": {"code": "0028400516464",               # Open Food Facts barcode (US product)
              "circle": "monosodium glutamate",        # must be on that label, word for word
              "circle_on": "monosodium glutamate",     # the words Kevin says it with (clip words)
              "show_on": "look at the label",          # optional: the card appears here (else ~4s before)
              "product": "Doritos Nacho Cheese"}       # optional: name on the card (else Open Food Facts')

Planner helper:  python3 kt_label.py find "doritos nacho cheese" "monosodium glutamate"
"""
import json
import math
import os
import re
import sys
import urllib.parse
import urllib.request

HOME = os.path.expanduser("~/Kamay")
CACHE = os.path.join(HOME, "work", "labels")
UA = {"User-Agent": "kt-factory-label-check/1.0"}
W_CARD, PAD, FPS = 780, 30, 30
FONTS = [("/System/Library/Fonts/Helvetica.ttc", 0, 1),
         ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", None, None)]


def _get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def _norm(t):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%]+", " ", str(t).lower())).strip()


# THE VERIFIED LABEL TRAVELS WITH THE PLAN (4 Nov 2026): the first cloud build of the Doritos clip
# came out with no card - the factory server could not read Open Food Facts, and said so nowhere.
# check_plan saves what it verified in the repo's factory/labels/, and the build reads it from there.
REPO_LABELS = [os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "factory", "labels")),
               os.path.join(HOME, "kt-machine", "factory", "labels")]


def fetch(code, save_to_repo=False):
    """{"code", "name", "ingredients"} from the repo's verified copy or Open Food Facts; None = no list."""
    code = re.sub(r"\D", "", str(code))
    if not code:
        return None
    for d in REPO_LABELS + [CACHE]:
        path = os.path.join(d, f"{code}.json")
        if os.path.exists(path):          # a copy check_plan verified and the planner committed
            try:
                return json.load(open(path))
            except ValueError:
                pass
    path = os.path.join(CACHE, f"{code}.json")
    d = _get(f"https://world.openfoodfacts.org/api/v2/product/{code}.json"
             "?fields=product_name,brands,ingredients_text_en,ingredients_text")
    p = d.get("product") or {}
    ing = (p.get("ingredients_text_en") or p.get("ingredients_text") or "").strip()
    if not ing:
        return None
    out = {"code": code, "name": (p.get("product_name") or "").strip(),
           "brands": (p.get("brands") or "").strip(), "ingredients": ing}
    os.makedirs(CACHE, exist_ok=True)
    json.dump(out, open(path, "w"), indent=1)
    if save_to_repo and os.path.isdir(os.path.dirname(REPO_LABELS[0])):
        os.makedirs(REPO_LABELS[0], exist_ok=True)
        json.dump(out, open(os.path.join(REPO_LABELS[0], f"{code}.json"), "w"), indent=1)
    return out


def check(label, save_to_repo=False):
    """(info, why). info is None when the label must not be shown - why says what is wrong."""
    if not isinstance(label, dict) or not label.get("code") or not label.get("circle"):
        return None, 'label needs "code" (Open Food Facts barcode) and "circle" (the ingredient)'
    try:
        info = fetch(label["code"], save_to_repo)
    except Exception as e:
        return None, f"label {label['code']}: could not read Open Food Facts ({type(e).__name__})"
    if not info:
        return None, f"label {label['code']}: Open Food Facts has no ingredient list for it"
    if f" {_norm(label['circle'])} " not in f" {_norm(info['ingredients'])} ":     # whole words: "oil" is not "boil"
        return None, (f"label {label['code']}: \"{label['circle']}\" is NOT on the real label - the "
                      f"claim is not backed (label: {info['ingredients'][:160]}...)")
    return info, ""


def find(query, ingredient=None, n=8):
    """Planner helper: US products matching a name, and whether each label carries the ingredient."""
    q = urllib.parse.urlencode({"search_terms": query, "search_simple": 1, "json": 1, "page_size": 24,
                                "fields": "code,product_name,brands,countries_tags,ingredients_text_en,"
                                          "ingredients_text"})
    d = _get("https://world.openfoodfacts.org/cgi/search.pl?" + q)
    rows = []
    for p in d.get("products", []):
        ing = p.get("ingredients_text_en") or p.get("ingredients_text") or ""
        if not ing or "en:united-states" not in (p.get("countries_tags") or []):
            continue
        has = None if not ingredient else f" {_norm(ingredient)} " in f" {_norm(ing)} "
        rows.append((p.get("code"), p.get("product_name"), p.get("brands"), has, ing))
    rows.sort(key=lambda r: (r[3] is not True,))
    return rows[:n]


# ---- timing -------------------------------------------------------------------------------------

def _at(words, phrase, after=0.0):
    """(start, end) of the first run of clip words matching `phrase`, starting at/after `after`."""
    want = _norm(phrase).split()
    toks = [_norm(w[2]) for w in words]
    if not want:
        return None
    for i in range(len(words)):
        if words[i][0] < after - 0.01:
            continue
        j, k = i, 0
        while j < len(words) and k < len(want):
            if not toks[j]:
                j += 1
                continue
            # "monosodium" may arrive as "mono sodium": join tokens until the wanted word is built
            got, jj = toks[j], j
            while got != want[k] and want[k].startswith(got) and jj + 1 < len(words):
                jj += 1
                got += toks[jj].replace(" ", "")
            if got != want[k]:
                break
            j, k = jj + 1, k + 1
        if k == len(want):
            return words[i][0], words[j - 1][1]
    return None


def times(label, words, dur):
    """(card_in, circle_a, circle_b, card_out) in clip seconds, or None when Kevin never says it."""
    c = _at(words, label.get("circle_on") or label["circle"])
    if not c:
        return None
    s = _at(words, label["show_on"]) if label.get("show_on") else None
    card_in = s[0] - 0.1 if s and s[0] < c[0] else c[0] - 4.0
    card_in = max(0.3, card_in)
    if c[0] - card_in > 9.0:                      # never sit on screen long before the point
        card_in = c[0] - 9.0
    a = max(card_in + 0.4, c[0] - 0.05)
    b = a + max(0.45, min(0.8, c[1] - c[0]))
    out = min(dur - 0.6, max(c[1] + 2.0, b + 1.6))
    if out - card_in < 2.5:
        return None
    return card_in, a, b, out


# ---- drawing ------------------------------------------------------------------------------------

def _font(size, bold=False):
    from PIL import ImageFont
    for path, reg, bld in FONTS:
        if os.path.exists(path):
            if path.endswith(".ttc"):
                return ImageFont.truetype(path, size, index=bld if bold else reg)
            return ImageFont.truetype(path.replace("-Regular", "-Bold") if bold else path, size)
    return ImageFont.truetype(os.path.join(HOME, "bin/arial_bold.ttf"), size)


def _layout(info, label, body=28, lh=37):
    target = label["circle"].upper()
    text = re.sub(r"\s+", " ", info["ingredients"]).strip().rstrip(".").upper()
    text = re.sub(r"^INGREDIENTS?\s*:\s*", "", text)
    # the target as one token, so the circle never has to cross a line break
    pos = text.upper().find(target)
    if pos >= 0:
        text = text[:pos] + target.replace(" ", " ") + text[pos + len(target):]
    f = _font(body)
    toks = ("INGREDIENTS: " + text).split(" ")
    lines, cur = [], ""
    for t in toks:
        trial = (cur + " " + t).strip()
        if f.getlength(trial.replace(" ", " ")) > W_CARD - 2 * PAD and cur:
            lines.append(cur)
            cur = t
        else:
            cur = trial
    lines.append(cur)
    y0, box, placed = PAD + 70, None, []
    for n, l in enumerate(lines):
        y = y0 + n * lh
        placed.append((PAD, y, l))
        key = target.replace(" ", " ")
        if key in l and box is None:
            x1 = PAD + f.getlength(l.split(key)[0].replace(" ", " "))
            box = (x1, y, x1 + _font(body, True).getlength(target), y + body)
    return placed, box, y0 + len(lines) * lh + 62, target


def card(info, label, progress, alpha, body=28):
    """One frame of the card (RGBA). progress 0..1 = how much of the circle is drawn."""
    from PIL import Image, ImageDraw
    placed, box, h, target = _layout(info, label, body)
    sc = 2
    im = Image.new("RGBA", (W_CARD * sc, h * sc), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, W_CARD * sc - 1, h * sc - 1], 10 * sc, fill=(250, 249, 246, 255))
    d.rectangle([PAD * sc, 18 * sc, (W_CARD - PAD) * sc, 22 * sc], fill=(20, 20, 20, 255))
    name = (label.get("product") or info.get("name") or "").upper()[:34]
    d.text((PAD * sc, 30 * sc), name, font=_font(30 * sc, True), fill=(20, 20, 20, 255))
    d.text((PAD * sc, (h - 44) * sc), f"As listed on the US label  ·  Open Food Facts {info['code']}",
           font=_font(19 * sc), fill=(90, 90, 90, 255))
    reg, bold = _font(body * sc), _font(body * sc, True)
    ink = (45, 45, 45, 255)
    if box and progress > 0:
        x1, y1, x2, y2 = box
        d.rectangle([(x1 - 4) * sc, (y1 - 3) * sc, (x2 + 4) * sc, (y2 + 5) * sc],
                    fill=(255, 226, 64, int(255 * min(1.0, progress * 1.5))))
    key = target.replace(" ", " ")
    for x, y, l in placed:
        parts = []
        if l.startswith("INGREDIENTS:"):
            parts.append(("INGREDIENTS: ", bold, (10, 10, 10, 255)))
            l = l[len("INGREDIENTS: "):]
        if key in l:
            pre, _, post = l.partition(key)
            parts += [(pre, reg, ink), (target, bold, (0, 0, 0, 255)), (post, reg, ink)]
        else:
            parts.append((l.replace(" ", " "), reg, ink))
        xx = x * sc
        for t, f, col in parts:
            d.text((xx, y * sc), t, font=f, fill=col)
            xx += f.getlength(t)
    if box and progress > 0:
        x1, y1, x2, y2 = box
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2 + 2
        rx, ry = (x2 - x1) / 2 + 20, (y2 - y1) / 2 + 11
        n = 90
        pts = []
        for i in range(int(n * 1.12 * progress) + 1):
            th = -2.4 + 2 * math.pi * 1.12 * i / n
            wob = 1 + 0.035 * math.sin(3 * th + 0.7) + 0.03 * (i / n)
            pts.append(((cx + rx * wob * math.cos(th)) * sc, (cy + ry * wob * math.sin(th) - 2 * i / n) * sc))
        if len(pts) > 1:
            d.line(pts, fill=(214, 32, 32, 255), width=7 * sc, joint="curve")
    im = im.resize((W_CARD, h), Image.LANCZOS)
    if alpha < 1:
        im.putalpha(im.split()[3].point(lambda v: int(v * alpha)))
    return im, h


def _ease(t):
    return 1 - (1 - max(0.0, min(1.0, t))) ** 3


def frames(info, label, t, out_dir):
    """Write the card's frames for times t = (in, circle_a, circle_b, out). -> (pattern, height)."""
    from PIL import Image
    card_in, ca, cb, card_out = t
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        if f.endswith(".png"):
            os.remove(os.path.join(out_dir, f))
    n = int(round((card_out - card_in) * FPS))
    h = 0
    cache = {}
    for i in range(n):
        tt = card_in + i / FPS
        a = _ease((tt - card_in) / 0.3) * (1 - _ease((tt - (card_out - 0.3)) / 0.3))
        p = _ease((tt - ca) / (cb - ca)) if tt >= ca else 0.0
        key = (round(a, 3), round(p, 3))
        if key not in cache:
            cache = {key: card(info, label, p, a)}
        im, h = cache[key]
        rise = int(24 * (1 - _ease((tt - card_in) / 0.3)))
        cv = Image.new("RGBA", (W_CARD, h + 24), (0, 0, 0, 0))
        cv.alpha_composite(im, (0, rise))
        cv.save(os.path.join(out_dir, f"c{i:04d}.png"))
    return os.path.join(out_dir, "c%04d.png"), h + 24


def place_y(h, cap_top, face_bottom=740):
    """Card top: its bottom 20px above the captions, never higher than just under the chin."""
    return int(max(min(face_bottom, cap_top - 20 - h), 560))


def main(argv):
    if len(argv) >= 2 and argv[0] == "find":
        for code, name, brands, has, ing in find(argv[1], argv[2] if len(argv) > 2 else None):
            mark = "" if has is None else ("  ON THE LABEL" if has else "  not on the label")
            print(f"{code}  {name} | {brands}{mark}\n    {ing[:220]}")
        return 0
    if len(argv) >= 2 and argv[0] == "check":
        info, why = check({"code": argv[1], "circle": " ".join(argv[2:])})
        print("OK - on the real label" if info else why)
        return 0 if info else 1
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
