import hashlib
import io
import json
import os
import re

import qrcode
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageOps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

CAT_KEY = "characters/whiskers"

BOARD_WIDTH = 1120

DEFAULT_SCALE = {
    "furniture": 0.7,
    "object": 0.5,
    "character": 0.45,
}

ROOM_LABELS = {
    "bedroom": "Bedroom",
    "living_room": "Living Room",
    "kitchen": "Kitchen",
    "bathroom": "Bathroom",
    "garden": "Garden",
}

_board_component = components.declare_component("whiskers_board", path=FRONTEND_DIR)


def pretty(name):
    return name.replace("_", " ").title()


def _open_cropped(path, max_size):
    image = Image.open(path).convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    if bbox:
        image = image.crop(bbox)
    width, height = image.size
    image.thumbnail((max_size, max_size), Image.LANCZOS)
    return image, width, height


GERADO_DIR = os.path.join(FRONTEND_DIR, "gerado")


def _arquivo_web(image, nome, quality=85):
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=quality)
    conteudo = buffer.getvalue()
    os.makedirs(GERADO_DIR, exist_ok=True)
    arquivo = re.sub(r"[^a-zA-Z0-9_-]", "_", nome) + ".webp"
    caminho = os.path.join(GERADO_DIR, arquivo)
    try:
        with open(caminho, "rb") as f:
            igual = f.read() == conteudo
    except OSError:
        igual = False
    if not igual:
        with open(caminho, "wb") as f:
            f.write(conteudo)
    versao = hashlib.md5(conteudo).hexdigest()[:8]
    return f"gerado/{arquivo}?v={versao}"


def _list_pngs(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(f for f in os.listdir(folder) if f.lower().endswith(".png"))


@st.cache_resource(show_spinner="Loading maps...")
def _load_all(assets_dir):
    assets, rooms = {}, []
    pil_items, pil_backgrounds = {}, {}

    def add_asset(key, path, name, kind):
        image, width, height = _open_cropped(path, max_size=420)
        pil_items[key] = image
        assets[key] = {
            "name": pretty(name),
            "kind": kind,
            "src": _arquivo_web(image, key),
            "ratio": height / width,
            "width": round(width * DEFAULT_SCALE[kind]),
        }

    character_path = os.path.join(assets_dir, "characters", "whiskers.png")
    if os.path.exists(character_path):
        add_asset(CAT_KEY, character_path, "whiskers", "character")

    for room in sorted(os.listdir(assets_dir)):
        background_path = os.path.join(assets_dir, room, "background.png")
        if not os.path.exists(background_path):
            continue

        background, bg_width, bg_height = _open_cropped(background_path, max_size=1600)
        pil_backgrounds[room] = background.convert("RGB")

        palette = []
        for kind, folder in (("furniture", "furniture"), ("object", "objects")):
            for file_name in _list_pngs(os.path.join(assets_dir, room, folder)):
                name = os.path.splitext(file_name)[0]
                key = f"{room}/{folder}/{name}"
                add_asset(key, os.path.join(assets_dir, room, folder, file_name), name, kind)
                palette.append(key)

        rooms.append({
            "id": room,
            "label": ROOM_LABELS.get(room, pretty(room)),
            "background": _arquivo_web(background, f"{room}/background"),
            "ratio": bg_height / bg_width,
            "palette": palette,
        })

    game_data = {"rooms": rooms, "assets": assets, "boardWidth": BOARD_WIDTH}
    return game_data, pil_items, pil_backgrounds


def game_data():
    return _load_all(ASSETS_DIR)[0]


def player_data(cena):
    data = game_data()
    room = next((r for r in data["rooms"] if r["id"] == cena["room"]), None)
    if room is None:
        return None
    keys = {it["key"] for it in cena["items"]} | {CAT_KEY}
    return {
        "rooms": [{**room, "palette": []}],
        "assets": {k: data["assets"][k] for k in keys if k in data["assets"]},
        "boardWidth": BOARD_WIDTH,
    }


def editor_board(height=720, key="editor"):
    return _board_component(
        data=game_data(), mode="editor", token="editor",
        height=height, key=key, default=None,
    )


def player_board(cena, vez_id, height=560, key="player"):
    data = player_data(cena)
    if data is None:
        st.error("O mapa desta cena não existe mais.")
        return None
    return _board_component(
        data=data, mode="player", scene=cena, turn=vez_id,
        token=f"player-{vez_id}-{cena['rev']}",
        height=height, key=key, default=None,
    )


def viewer_board(cena, cat=None, height=600, key="viewer"):
    data = player_data(cena)
    if data is None:
        return None
    return _board_component(
        data=data, mode="viewer", scene=cena, cat=cat,
        token=f"viewer-{cena['rev']}",
        height=height, key=key, default=None,
    )


@st.cache_data(show_spinner=False, max_entries=300)
def _render_scene(scene_json, cat_json, width):
    scene = json.loads(scene_json)
    cat = json.loads(cat_json) if cat_json else None
    data, pil_items, pil_backgrounds = _load_all(ASSETS_DIR)
    assets = data["assets"]

    background = pil_backgrounds[scene["room"]]
    room = next(r for r in data["rooms"] if r["id"] == scene["room"])
    s = width / BOARD_WIDTH
    height = round(width * room["ratio"])
    canvas = background.resize((width, height), Image.LANCZOS).convert("RGBA")

    items = [it for it in scene["items"] if it["key"] in pil_items]
    if cat and CAT_KEY in pil_items:
        items.append({**cat, "key": CAT_KEY})

    for it in sorted(items, key=lambda i: i.get("z", 0)):
        w = max(1, round(it["w"] * s))
        h = max(1, round(it["w"] * assets[it["key"]]["ratio"] * s))
        image = pil_items[it["key"]].resize((w, h), Image.LANCZOS)
        if it.get("flip"):
            image = ImageOps.mirror(image)
        if it.get("rot"):
            image = image.rotate(-it["rot"], resample=Image.BICUBIC, expand=True)
        x = round(it["x"] * s - image.width / 2)
        y = round(it["y"] * s - image.height / 2)
        canvas.paste(image, (x, y), image)

    buffer = io.BytesIO()
    canvas.convert("RGB").save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def scene_image(cena, cat=None, width=1000):
    scene_json = json.dumps({"room": cena["room"], "items": cena["items"]}, sort_keys=True)
    cat_json = json.dumps(cat, sort_keys=True) if cat else ""
    return _render_scene(scene_json, cat_json, width)


@st.cache_data(show_spinner=False)
def qr_png(url):
    qr = qrcode.QRCode(border=2, box_size=10, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#46178f", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
