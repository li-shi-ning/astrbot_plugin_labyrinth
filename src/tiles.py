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

# 方向编号
NORTH, EAST, SOUTH, WEST = 0, 1, 2, 3
DIRS = {NORTH: (-1, 0), EAST: (0, 1), SOUTH: (1, 0), WEST: (0, -1)}
OPPOSITE = {NORTH: SOUTH, EAST: WEST, SOUTH: NORTH, WEST: EAST}

BOARD_SIZE = 7
CORNERS = 4

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


def treasure_name(treasure: str) -> str:
    """宝藏的中文名（未知 id 原样返回）。"""
    return TREASURE_NAMES.get(treasure, treasure)


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
