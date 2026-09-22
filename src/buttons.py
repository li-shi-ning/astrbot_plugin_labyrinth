"""根据牌局状态生成 QQ 官方键盘。

布局约定（每行 4 个、最多 5 行）::

    第 1 行   🎯 A·目标 | 🎯 B·目标 | 🎯 C·目标 | 🎯 D·目标
    第 2-4 行 推上b | 推下b | 推左2 | 推右2      （一列一边，上下按列字母、左右按行号）
    第 5 行   转手牌 | 棋盘状态 | 玩法规则 | 解散牌局

移动阶段只给一个「移动」按钮（点完变成「迷宫 走 」，坐标自己补）和「停手」。
"""

from __future__ import annotations

from .engine import PHASE_ENDED, PHASE_MOVE, PHASE_PUSH, Game
from .qqofficial import Button
from .render import target_payload
from .tiles import PUSH_LINES, push_line_name

PUBLIC_BUTTONS = ("棋盘状态", "玩法规则")


def build_buttons(
    game: Game | None, requester_id: str, is_admin: bool = False
) -> list[Button]:
    """按当前状态返回一组按钮。"""
    if game is None:
        return [
            Button("lab_create", "创建牌局", "迷宫 创建"),
            Button("lab_rules", "玩法规则", "迷宫 规则"),
        ]
    if not game.started:
        return _waiting_buttons(game, requester_id, is_admin)
    return _playing_buttons(game, requester_id, is_admin)


def _waiting_buttons(game: Game, requester_id: str, is_admin: bool) -> list[Button]:
    buttons = [Button("lab_join", "加入牌局", "迷宫 加入")]
    host = game.players[0] if game.players else None
    if host is not None and len(game.players) >= 2:
        buttons.append(
            Button("lab_start", "开始游戏", "迷宫 开始", only_for=host.user_id)
        )
    if game.find(requester_id) is not None:
        buttons.append(Button("lab_leave", "退出牌局", "迷宫 退出"))
    buttons.extend(_public_buttons(game, requester_id, is_admin))
    return buttons


def _playing_buttons(game: Game, requester_id: str, is_admin: bool) -> list[Button]:
    buttons: list[Button] = []

    # 第 1 行：私密目标（每人一个，只有本人可点）
    for index, player in enumerate(game.players):
        buttons.append(
            Button(
                f"lab_target_{index}",
                f"🎯 {game.label_of(player)}·目标",
                target_payload(player, game),
                only_for=player.user_id,
                new_row=index == 0,
            )
        )

    current = game.current
    if current is not None and game.phase != PHASE_ENDED:
        actor = current.user_id
        if game.phase == PHASE_PUSH:
            # 第 2-4 行：一列一边
            # 列方向按 a→g 取 b/d/f；行方向按「行号从小到大」取 2/4/6（内部下标倒序）
            column_lines = list(PUSH_LINES)
            row_lines = list(reversed(PUSH_LINES))
            for index in range(len(PUSH_LINES)):
                for side, line in (
                    ("上", column_lines[index]),
                    ("下", column_lines[index]),
                    ("左", row_lines[index]),
                    ("右", row_lines[index]),
                ):
                    name = push_line_name(side, line)
                    buttons.append(
                        Button(
                            f"lab_push_{side}_{line}",
                            f"推{side}{name}",
                            f"迷宫 推 {side} {name}",
                            only_for=actor,
                            new_row=side == "上",
                        )
                    )
            buttons.append(
                Button("lab_rotate", "转手牌", "迷宫 转", only_for=actor, new_row=True)
            )
        elif game.phase == PHASE_MOVE:
            # 只给一个「移动」按钮：点完补成「迷宫 走 」，坐标自己填，引擎校验可达性
            buttons.append(
                Button("lab_move", "移动", "迷宫 走 ", only_for=actor, new_row=True)
            )
            buttons.append(Button("lab_stop", "停手", "迷宫 停", only_for=actor))

    buttons.extend(_public_buttons(game, requester_id, is_admin, join_row=True))
    return buttons


def _public_buttons(
    game: Game, requester_id: str, is_admin: bool, join_row: bool = False
) -> list[Button]:
    """棋盘状态 / 玩法规则 / 解散牌局（房主或管理员可点）。"""
    buttons = [
        Button("lab_state", "棋盘状态", "迷宫 状态", new_row=not join_row),
        Button("lab_rules", "玩法规则", "迷宫 规则"),
    ]
    host = game.players[0] if game.players else None
    if host is not None:
        allowed = requester_id if is_admin else host.user_id
        buttons.append(
            Button("lab_dissolve", "解散牌局", "迷宫 解散", only_for=allowed)
        )
    return buttons
