"""把 7×7 迷宫渲染成一张本地 PNG（QQ 富媒体上传用）。

素材约定（都放在插件 ``assets/`` 下，缺失时自动用几何图形兜底）::

    assets/tiles/straight.png      牌型基础图（rotation=0 的朝向，代码负责旋转）
    assets/tiles/corner.png
    assets/tiles/t-shape.png
    assets/treasures/<TreasureId>.png   宝藏图标，画在牌中央
    assets/pawns/<color>.png            棋子（yellow/red/blue/green）
    assets/font.ttf                     可选，中文字体

缺素材时用 Pillow 直接画通道与文字，因此没有图片也能正常出图。
"""

from __future__ import annotations

import os
from pathlib import Path

from .engine import PUSH_LINES, Game, Player, Tile
from .tiles import BOARD_SIZE, COLUMN_LETTERS, DIRS, treasure_name

DIRECTION_CN = {0: "上", 1: "右", 2: "下", 3: "左"}

ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
TILE_DIR = ASSET_DIR / "tiles"
TREASURE_DIR = ASSET_DIR / "treasures"
PAWN_DIR = ASSET_DIR / "pawns"

CELL = 64
MARGIN = 30
SIDE_PANEL = 208  # 棋盘右侧「手牌卡 + 玩家进度」区域宽度
SPARE_SIZE = 120  # 手牌放大展示尺寸
PLAYER_ROW_H = 38  # 右侧玩家进度每行高度
PANEL_BG = (255, 255, 255)

WALL = (214, 196, 165)
FLOOR = (252, 248, 238)
LINE = (176, 156, 124)
BG = (246, 247, 250)
FG = (32, 33, 36)
MUTED = (150, 152, 160)
HIGHLIGHT = (255, 222, 120)
ARROW = (108, 122, 156)

def _font_candidates() -> tuple[str, ...]:
    candidates = [
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    windir = os.environ.get("WINDIR")
    if windir:
        candidates.insert(0, str(Path(windir) / "Fonts" / "msyh.ttc"))
    return tuple(candidates)


FONT_CANDIDATES = _font_candidates()

PAWN_COLORS = {
    "yellow": (240, 180, 30),
    "red": (214, 69, 65),
    "blue": (52, 120, 210),
    "green": (66, 160, 90),
}


def find_font() -> str | None:
    """返回第一个可用的字体路径。"""
    for path in FONT_CANDIDATES:
        if Path(path).is_file():
            return path
    return None


def render_board(
    game: Game,
    out_path: str | Path,
    font_path: str | None = None,
    reveal_hidden: bool = False,
):
    """渲染整张棋盘，返回输出路径；缺少 Pillow 时返回 ``None``。

    Args:
        game: 牌局。
        out_path: 输出 PNG 路径。
        font_path: 中文字体路径，留空自动查找。
        reveal_hidden: 调试用，未使用（接口保留）。
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:  # pragma: no cover - AstrBot 自带 Pillow
        return None

    font_file = font_path or find_font()

    def font(size: int):
        if font_file:
            try:
                return ImageFont.truetype(font_file, size)
            except OSError:
                pass
        return ImageFont.load_default(size=size)

    board_px = BOARD_SIZE * CELL
    width = MARGIN * 2 + board_px + SIDE_PANEL
    height = MARGIN * 2 + board_px
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)
    f_small = font(15)
    f_tiny = font(13)
    f_label = font(17)

    origin_x, origin_y = MARGIN, MARGIN

    def cell_box(row: int, col: int) -> tuple[int, int, int, int]:
        x = origin_x + col * CELL
        y = origin_y + row * CELL
        return x, y, x + CELL, y + CELL

    # 当前玩家高亮
    current = game.current
    if current is not None and game.phase != "ended":
        x0, y0, x1, y1 = cell_box(*current.pos)
        draw.rectangle([x0 - 2, y0 - 2, x1 + 1, y1 + 1], outline=HIGHLIGHT, width=4)

    # 棋盘
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            tile = game.tile(row, col)
            x0, y0, _x1, _y1 = cell_box(row, col)
            image.paste(_render_tile(tile), (x0, y0))
            draw.rectangle([x0, y0, x0 + CELL - 1, y0 + CELL - 1], outline=LINE)

    # 可推线的箭头
    for index in PUSH_LINES:
        x0, y0, x1, y1 = cell_box(0, index)
        _arrow(draw, x0 + CELL // 2, y0 - 12, "down", ARROW)
        x0, y0, x1, y1 = cell_box(BOARD_SIZE - 1, index)
        _arrow(draw, x0 + CELL // 2, y1 + 12, "up", ARROW)
        x0, y0, x1, y1 = cell_box(index, 0)
        _arrow(draw, x0 - 12, y0 + CELL // 2, "right", ARROW)
        x0, y0, x1, y1 = cell_box(index, BOARD_SIZE - 1)
        _arrow(draw, x1 + 12, y0 + CELL // 2, "left", ARROW)

    # 坐标：上方 a-g（左→右），左侧 1-7（下→上）
    for index in range(BOARD_SIZE):
        x0, _y0, _x1, _y1 = cell_box(0, index)
        draw.text(
            (x0 + CELL // 2 - 5, origin_y - 26),
            COLUMN_LETTERS[index],
            font=f_small,
            fill=FG,
        )
        _x0, y0, _x1, _y1 = cell_box(index, 0)
        draw.text(
            (origin_x - 26, y0 + CELL // 2 - 8),
            str(BOARD_SIZE - index),
            font=f_small,
            fill=FG,
        )

    # 棋子
    for index, player in enumerate(game.players):
        x0, y0, _x1, _y1 = cell_box(*player.pos)
        _draw_pawn(image, draw, f_label, player, index, x0, y0)

    # 右侧：独立的手牌卡 + 玩家进度
    panel_x0 = origin_x + board_px + 14
    panel_x1 = width - MARGIN
    panel_w = panel_x1 - panel_x0
    draw.rounded_rectangle(
        [panel_x0, origin_y, panel_x1, origin_y + board_px],
        radius=12,
        fill=PANEL_BG,
        outline=LINE,
        width=2,
    )

    def center_text(y: int, text: str, text_font, fill) -> None:
        cx = (panel_x0 + panel_x1) // 2
        draw.text(
            (cx - draw.textlength(text, font=text_font) / 2, y),
            text,
            font=text_font,
            fill=fill,
        )

    cursor = origin_y + 14
    center_text(cursor, "手 牌", f_label, FG)
    cursor += 28

    if game.spare is not None:
        spare_image = _render_tile(game.spare, SPARE_SIZE)
        image.paste(spare_image, (panel_x0 + (panel_w - SPARE_SIZE) // 2, cursor))
        cursor += SPARE_SIZE + 8
        rotation_cn = {0: "上右", 1: "右下", 2: "下左", 3: "左上"}
        center_text(cursor, f"朝向 {rotation_cn[game.spare.rotation]}", f_small, FG)
        cursor += 22
        openings = " ".join(DIRECTION_CN[d] for d in sorted(game.spare.openings()))
        center_text(cursor, f"开口 {openings}", f_tiny, MUTED)
        cursor += 20

    draw.line([panel_x0 + 16, cursor, panel_x1 - 16, cursor], fill=LINE, width=1)
    cursor += 10
    draw.text((panel_x0 + 16, cursor), "上下推 → 选列 b/d/f", font=f_tiny, fill=MUTED)
    cursor += 18
    draw.text((panel_x0 + 16, cursor), "左右推 → 选行 2/4/6", font=f_tiny, fill=MUTED)
    cursor += 20

    draw.line([panel_x0 + 16, cursor, panel_x1 - 16, cursor], fill=LINE, width=1)
    cursor += 10

    for index, player in enumerate(game.players):
        label = f"{chr(ord('A') + index)} {player.name}"[:10]
        active = player is current
        draw.text(
            (panel_x0 + 16, cursor),
            label,
            font=f_small,
            fill=FG if active else MUTED,
        )
        cursor += 19
        text = f"　已收 {player.collected}/{len(player.treasures)}"
        if player.all_collected:
            text += "　回起点"
        draw.text((panel_x0 + 16, cursor), text, font=f_tiny, fill=MUTED)
        cursor += PLAYER_ROW_H - 19

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, "PNG")
    return out_path


# ----------------------------------------------------------------------
# 单张牌
# ----------------------------------------------------------------------
def _render_tile(tile: Tile, size: int = CELL):
    """渲染一张牌：先取牌型底图，再把宝藏图标贴上去。"""
    from PIL import ImageDraw

    image = _tile_base(tile, size)
    if tile.treasure:
        _draw_treasure(image, ImageDraw.Draw(image), tile.treasure, size)
    return image


def _tile_base(tile: Tile, size: int = CELL):
    """牌型底图（已按 ``tile.rotation`` 顺时针旋转）。

    优先用 ``assets/tiles/<kind>.png``（rotation=0 的朝向），
    缺失时按出口程序化画一张。
    """
    from PIL import Image

    path = TILE_DIR / f"{tile.kind}.png"
    if path.is_file():
        try:
            with Image.open(path) as source:
                base = source.convert("RGBA").resize((size, size), Image.LANCZOS)
        except (OSError, ValueError):
            base = None
        if base is not None:
            if tile.rotation:
                # Pillow 正角度是逆时针，取负号得到顺时针
                base = base.rotate(-90 * tile.rotation)
            canvas = Image.new("RGB", (size, size), WALL)
            canvas.paste(base, (0, 0), base)
            return canvas
    return _draw_base(tile, size)


def _draw_base(tile: Tile, size: int = CELL):
    """没有素材时按出口程序化画通道。"""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (size, size), WALL)
    draw = ImageDraw.Draw(image)
    half = size // 2
    thickness = max(6, size * 16 // CELL)
    for direction in tile.openings():
        dr, dc = DIRS[direction]
        if dr == -1:
            draw.rectangle(
                [half - thickness // 2, 0, half + thickness // 2, half], fill=FLOOR
            )
        elif dr == 1:
            draw.rectangle(
                [half - thickness // 2, half, half + thickness // 2, size], fill=FLOOR
            )
        elif dc == 1:
            draw.rectangle(
                [half, half - thickness // 2, size, half + thickness // 2], fill=FLOOR
            )
        else:
            draw.rectangle(
                [0, half - thickness // 2, half, half + thickness // 2], fill=FLOOR
            )
    draw.rectangle(
        [
            half - thickness // 2,
            half - thickness // 2,
            half + thickness // 2,
            half + thickness // 2,
        ],
        fill=FLOOR,
    )
    return image


def _draw_treasure(image, draw, treasure: str, size: int = CELL) -> None:
    """宝藏图标：有素材就贴图，否则画个圆圈写名字。"""
    path = TREASURE_DIR / f"{treasure}.png"
    if path.is_file():
        try:
            from PIL import Image

            with Image.open(path) as icon:
                icon = icon.convert("RGBA")
                icon_size = size // 2
                icon = icon.resize((icon_size, icon_size), Image.LANCZOS)
                image.paste(
                    icon, ((size - icon_size) // 2, (size - icon_size) // 2), icon
                )
                return
        except (OSError, ValueError):
            pass
    font = _font(14)
    text = treasure_name(treasure)
    draw.ellipse(
        [CELL // 4, CELL // 4, CELL * 3 // 4, CELL * 3 // 4],
        fill=(255, 255, 255),
        outline=(120, 120, 120),
    )
    draw.text(
        (CELL // 2, CELL // 2), text[:2], font=font, fill=(40, 40, 40), anchor="mm"
    )


def _draw_pawn(image, draw, font, player: Player, index: int, x0: int, y0: int) -> None:
    path = PAWN_DIR / f"{player.color}.png"
    size = CELL - 22
    if path.is_file():
        try:
            from PIL import Image

            with Image.open(path) as pawn:
                pawn = pawn.convert("RGBA").resize((size, size), Image.LANCZOS)
                image.paste(pawn, (x0 + 11, y0 + 11), pawn)
                return
        except (OSError, ValueError):
            pass
    color = PAWN_COLORS.get(player.color, (120, 120, 120))
    box = [x0 + 13, y0 + 13, x0 + CELL - 13, y0 + CELL - 13]
    draw.ellipse(box, fill=color, outline=(255, 255, 255), width=3)
    draw.text(
        ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2),
        chr(ord("A") + index),
        font=font,
        fill=(255, 255, 255),
        anchor="mm",
    )


def _arrow(draw, x: int, y: int, direction: str, color) -> None:
    size = 7
    if direction == "down":
        draw.polygon(
            [(x - size, y - size), (x + size, y - size), (x, y + size)], fill=color
        )
    elif direction == "up":
        draw.polygon(
            [(x - size, y + size), (x + size, y + size), (x, y - size)], fill=color
        )
    elif direction == "right":
        draw.polygon(
            [(x - size, y - size), (x - size, y + size), (x + size, y)], fill=color
        )
    else:
        draw.polygon(
            [(x + size, y - size), (x + size, y + size), (x - size, y)], fill=color
        )


_FONT_CACHE: dict[tuple[str | None, int], object] = {}


def _font(size: int):
    from PIL import ImageFont

    key = (find_font(), size)
    if key not in _FONT_CACHE:
        path = key[0]
        if path:
            try:
                _FONT_CACHE[key] = ImageFont.truetype(path, size)
            except OSError:
                _FONT_CACHE[key] = ImageFont.load_default(size=size)
        else:
            _FONT_CACHE[key] = ImageFont.load_default(size=size)
    return _FONT_CACHE[key]
