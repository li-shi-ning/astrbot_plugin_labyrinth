"""Labyrinth（疯狂迷宫）的牌堆与棋盘常量。

数据来自雷文斯堡原版《Das verrückte Labyrinth》：

* 棋盘 7×7 = 49 格，其中 16 格是印在棋盘上的**固定牌**（偶数行 × 偶数列），
  其余 33 格放**可移动牌**；可移动牌共 34 张，多出的 1 张是手牌（spare）。
* 12 个箭头 → 可推的 6 条线（第 1/3/5 行与第 1/3/5 列，0 基），每条线两端各一个箭头。
* 共 24 张宝藏卡：固定牌 12 张 + 可移动牌 12 张。

牌型（rotation=0 时的出口，方向编号 0=上 1=右 2=下 3=左）：::

    straight  上下
    corner    上右
    t-shape   上右下
"""

from __future__ import annotations

import re

# 方向编号
NORTH, EAST, SOUTH, WEST = 0, 1, 2, 3
DIRS = {NORTH: (-1, 0), EAST: (0, 1), SOUTH: (1, 0), WEST: (0, -1)}
OPPOSITE = {NORTH: SOUTH, EAST: WEST, SOUTH: NORTH, WEST: EAST}

BOARD_SIZE = 7
CORNERS = 4

# 玩家看到的坐标：列 a-g 从左到右，行 1-7 从下到上（左下角是 a1）
COLUMN_LETTERS = "abcdefg"

# 可推的行/列（内部 0 基下标）：第 b/d/f 列与第 2/4/6 行
PUSH_LINES = (1, 3, 5)

# 各牌型在 rotation=0 时的出口
BASE_OPENINGS: dict[str, tuple[int, ...]] = {
    "straight": (NORTH, SOUTH),
    "corner": (NORTH, EAST),
    "t-shape": (NORTH, EAST, SOUTH),
}

# 24 张宝藏（12 张在固定牌上，12 张在可移动牌上）
# id 与素材包 assets/treasures/<id>.png 一一对应
FIXED_TREASURES = (
    "Helmet",
    "Candelabra",
    "Sword",
    "Jewel",
    "TreasureChest",
    "Ring",
    "TreasureMap",
    "Keys",
    "Crown",
    "GhostInBottle",
    "BagOfGold",
    "Book",
)
LOOSE_TREASURES = (
    "Rat",
    "Bat",
    "Owl",
    "Lizard",
    "Spider",
    "Moth",
    "Scarab",
    "Skull",
    "Dragon",
    "Princess",
    "Sorceress",
    "Ghost",
)
TREASURES = FIXED_TREASURES + LOOSE_TREASURES

TREASURE_NAMES = {
    "Helmet": "骑士头盔",
    "Candelabra": "烛台",
    "Sword": "剑",
    "Jewel": "宝石",
    "TreasureChest": "宝箱",
    "Ring": "戒指",
    "TreasureMap": "藏宝图",
    "Keys": "钥匙",
    "Crown": "王冠",
    "GhostInBottle": "瓶中幽灵",
    "BagOfGold": "金币袋",
    "Book": "书",
    "Rat": "老鼠",
    "Bat": "蝙蝠",
    "Owl": "猫头鹰",
    "Lizard": "蜥蜴",
    "Spider": "蜘蛛",
    "Moth": "飞蛾",
    "Scarab": "圣甲虫",
    "Skull": "骷髅",
    "Dragon": "龙",
    "Princess": "公主",
    "Sorceress": "女巫",
    "Ghost": "幽灵",
}


# 每个宝藏的 emoji（用于对玩家展示）
TREASURE_EMOJI = {
    "Helmet": "🪖",
    "Candelabra": "🕯️",
    "Sword": "⚔️",
    "Jewel": "💎",
    "TreasureChest": "🧰",
    "Ring": "💍",
    "TreasureMap": "🗺️",
    "Keys": "🔑",
    "Crown": "👑",
    "GhostInBottle": "⚗️",
    "BagOfGold": "💰",
    "Book": "📖",
    "Rat": "🐀",
    "Bat": "🦇",
    "Owl": "🦉",
    "Lizard": "🦎",
    "Spider": "🕷️",
    "Moth": "🦋",
    "Scarab": "🪲",
    "Skull": "💀",
    "Dragon": "🐉",
    "Princess": "👸",
    "Sorceress": "🧙",
    "Ghost": "👻",
}


def treasure_name(treasure: str) -> str:
    """宝藏的中文名（未知 id 原样返回）。"""
    return TREASURE_NAMES.get(treasure, treasure)


def treasure_label(treasure: str) -> str:
    """给玩家看的宝藏文字：``emoji + 中文名``，如 ``🐉 龙``。"""
    emoji = TREASURE_EMOJI.get(treasure)
    name = treasure_name(treasure)
    return f"{emoji} {name}" if emoji else name


# 16 张固定牌：(行, 列) -> (牌型, rotation, 宝藏, 起始角颜色)
FIXED_TILES: dict[tuple[int, int], tuple[str, int, str | None, str | None]] = {
    (0, 0): ("corner", 1, None, "yellow"),
    (0, 2): ("t-shape", 1, "Helmet", None),
    (0, 4): ("t-shape", 1, "Candelabra", None),
    (0, 6): ("corner", 2, None, "red"),
    (2, 0): ("t-shape", 0, "Sword", None),
    (2, 2): ("t-shape", 0, "Jewel", None),
    (2, 4): ("t-shape", 1, "TreasureChest", None),
    (2, 6): ("t-shape", 2, "Ring", None),
    (4, 0): ("t-shape", 0, "TreasureMap", None),
    (4, 2): ("t-shape", 3, "Keys", None),
    (4, 4): ("t-shape", 2, "Crown", None),
    (4, 6): ("t-shape", 2, "GhostInBottle", None),
    (6, 0): ("corner", 0, None, "green"),
    (6, 2): ("t-shape", 3, "BagOfGold", None),
    (6, 4): ("t-shape", 3, "Book", None),
    (6, 6): ("corner", 3, None, "blue"),
}

# 可移动牌构成：12 直线 + 10 曲线 + 6 曲线(带宝藏) + 6 三通(带宝藏) = 34
LOOSE_BAG: tuple[tuple[str, str | None], ...] = (
    *(("straight", None) for _ in range(12)),
    *(("corner", None) for _ in range(10)),
    ("corner", "Rat"),
    ("corner", "Bat"),
    ("corner", "Owl"),
    ("corner", "Lizard"),
    ("corner", "Spider"),
    ("corner", "Moth"),
    ("t-shape", "Scarab"),
    ("t-shape", "Skull"),
    ("t-shape", "Dragon"),
    ("t-shape", "Princess"),
    ("t-shape", "Sorceress"),
    ("t-shape", "Ghost"),
)

# 玩家起始角（按加入顺序），2 人局为对角
START_POSITIONS: tuple[tuple[tuple[int, int], str], ...] = (
    ((0, 0), "yellow"),
    ((6, 6), "blue"),
    ((0, 6), "red"),
    ((6, 0), "green"),
)

COLOR_NAMES = {
    "yellow": "黄",
    "red": "红",
    "blue": "蓝",
    "green": "绿",
}


def push_lines() -> tuple[int, ...]:
    """可推的行/列下标（0 基）。"""
    return (1, 3, 5)


# ----------------------------------------------------------------------
# 坐标
# ----------------------------------------------------------------------
def column_index(letter: str) -> int | None:
    """列字母 a-g → 内部列下标；非法返回 ``None``。"""
    letter = (letter or "").strip().lower()
    if len(letter) == 1 and letter in COLUMN_LETTERS:
        return COLUMN_LETTERS.index(letter)
    return None


def cell_name(row: int, col: int) -> str:
    """内部 ``(row, col)`` → 玩家坐标，如 ``c3``（列 a-g，行 1-7 下→上）。"""
    return f"{COLUMN_LETTERS[col]}{BOARD_SIZE - row}"


def parse_cell(text: str) -> tuple[int, int] | None:
    """解析玩家坐标 ``c3`` / ``C3`` / ``3c`` → 内部 ``(row, col)``。"""
    text = (text or "").strip()
    match = re.fullmatch(r"([a-gA-G])\s*([1-7])", text)
    if match:
        col = column_index(match.group(1))
        return BOARD_SIZE - int(match.group(2)), col
    match = re.fullmatch(r"([1-7])\s*([a-gA-G])", text)
    if match:
        col = column_index(match.group(2))
        return BOARD_SIZE - int(match.group(1)), col
    return None


def push_line_name(side: str, index: int) -> str:
    """推牌对象的展示名：上下按列字母（b/d/f），左右按行号（2/4/6）。"""
    if side in ("上", "下"):
        return COLUMN_LETTERS[index]
    return str(BOARD_SIZE - index)


def parse_push_line(side: str, token: str) -> int | None:
    """把推牌的列字母/行号解析成内部下标；不在可推线上返回 ``None``。"""
    if side in ("上", "下"):
        index = column_index(token)
        return index if index in PUSH_LINES else None
    token = (token or "").strip()
    if token.isdigit() and 1 <= int(token) <= BOARD_SIZE:
        index = BOARD_SIZE - int(token)
        return index if index in PUSH_LINES else None
    return None
