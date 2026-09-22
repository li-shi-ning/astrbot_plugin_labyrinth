"""把对局状态渲染成聊天文本与按钮数据。"""

from __future__ import annotations

from .engine import PHASE_ENDED, PHASE_PUSH, Game, Player
from .tiles import COLOR_NAMES, treasure_label

ROTATION_CN = {0: "上右", 1: "右下", 2: "下左", 3: "左上"}


def render_menu() -> str:
    return "🌀 疯狂迷宫 · 点击下方按钮开局（规则见「玩法规则」）"


def render_table(game: Game) -> str:
    """公开牌桌文本（发送棋盘图片时只留一行摘要）。"""
    if not game.started:
        return "\n".join(
            [
                "当前牌局：",
                *(f"{chr(ord('A') + i)} {p.name}" for i, p in enumerate(game.players)),
            ]
        )
    lines = [f"🌀 疯狂迷宫 · 第 {game.turn_index + 1} 位行动", ""]
    for index, player in enumerate(game.players):
        label = chr(ord("A") + index)
        found = "、".join(treasure_label(t) for t in player.found) or "无"
        lines.append(
            f"{label} {player.name}（{COLOR_NAMES.get(player.color, '?')}）"
            f" 已收 {player.collected}/{len(player.treasures)}：{found}"
        )
    return "\n".join(lines)


def render_hint(game: Game) -> str:
    """当前阶段该做什么。"""
    if game.phase == PHASE_ENDED:
        winner = game.find(game.winner or "")
        if winner is None:
            return "对局结束。"
        index = game.players.index(winner)
        return f"🏁 {chr(ord('A') + index)} {winner.name} 获胜！"
    current = game.current
    if current is None:
        return ""
    label = game.label_of(current)
    if game.phase == PHASE_PUSH:
        spare = game.spare
        facing = ROTATION_CN[spare.rotation] if spare else "?"
        return (
            f"▶ 轮到 {label} {current.name}：手牌朝向「{facing}」，"
            "先推牌（可先「迷宫 转」旋转手牌）\n"
            "格式：迷宫 推 上 2（上/下/左/右 + 2/4/6）"
        )
    cells = sorted(game.reachable(current))
    listed = " ".join(f"{r + 1}-{c + 1}" for r, c in cells[:28])
    if len(cells) > 28:
        listed += " …"
    return (
        f"▶ {label} {current.name} 已推入棋盘\n"
        f"可达格子：{listed}\n"
        "移动：迷宫 走 行 列（或「迷宫 停」不移动直接结束）"
    )


def render_push(result) -> str:
    text = (
        f"🧩 {result.side} {result.index + 1} 推入，"
        f"推出 {result.ejected[0] + 1}-{result.ejected[1] + 1}"
    )
    if result.collected:
        text += "\n" + _collected_text(result.collected)
    if result.winner:
        text += "\n" + _win_text(result.winner)
    return text


def render_move(result) -> str:
    if result.stayed:
        text = "🧍 原地不动，回合结束"
    else:
        text = "🚶 移动完成"
    if result.collected:
        text += "\n" + _collected_text(result.collected)
    if result.winner:
        text += "\n" + _win_text(result.winner)
    return text


def _collected_text(collected: list[tuple[str, str]]) -> str:
    return "\n".join(f"🎁 找到【{treasure_label(t)}】" for _uid, t in collected)


def _win_text(user_id: str) -> str:
    return "🏁 集齐全部宝藏并回到起点，获胜！"


def target_payload(player: Player, game: Game) -> str:
    """私密按钮 data：只看得到自己的当前目标。"""
    if player.target is None:
        return f"🎯 {game.label_of(player)} 目标：已全部集齐，回起点（看完请勿发送）"
    return f"🎯 {game.label_of(player)} 目标：{treasure_label(player.target)}（看完请勿发送）"


def target_text(player: Player, game: Game) -> str:
    if player.target is None:
        return "🎯 你已经集齐全部宝藏，现在回到起点即可获胜。"
    return f"🎯 {game.label_of(player)} 当前目标：【{treasure_label(player.target)}】"


def render_help() -> str:
    return (
        "疯狂迷宫\n"
        "1. 创建/加入 → 房主「开始游戏」（2-4 人）\n"
        "2. 每回合先推牌：迷宫 推 上 2（可先「迷宫 转」旋转手牌）\n"
        "3. 再移动：迷宫 走 行 列（棋盘行列都从 1 开始），或「迷宫 停」\n"
        "4. 走到自己目标宝藏那一格即收集，集齐后回起点获胜\n"
        "目标只在「目标」按钮里可见，完整规则见「迷宫 规则」"
    )


def render_rules() -> str:
    return (
        "疯狂迷宫 · 规则\n"
        "1. 棋盘 7×7：16 格是固定牌，33 格是可移动牌，另有 1 张手牌。\n"
        "2. 每回合必须先插入手牌：只能推第 2/4/6 行或列（图上箭头处），"
        "插入后对端会被挤出一张牌，成为你的新手牌；可以把牌推出棋盘。\n"
        "3. 不能把上一手刚推出的位置原路推回去；插入前可以任意旋转手牌。\n"
        "4. 推牌会带动整条线上的棋子；被挤出棋盘的棋子放到新插入的那格。\n"
        "5. 推完可以沿通道任意走（也可以不走）；棋子可以重叠。\n"
        "6. 走到自己当前目标宝藏所在格即收集，换下一张目标；"
        "集齐全部目标后回到自己的起点格获胜。\n"
        "7. 2 人各 12 张目标，3 人各 8 张，4 人各 6 张。"
    )
