"""根据牌局状态生成 QQ 官方键盘（私密目标按钮用 only_for）。"""

from __future__ import annotations

from .engine import PHASE_ENDED, PHASE_MOVE, PHASE_PUSH, PUSH_LINES, Game
from .qqofficial import Button
from .render import target_payload


def build_buttons(game: Game | None, requester_id: str) -> list[Button]:
    """按当前状态返回一组按钮。"""
    if game is None:
        return [
            Button("lab_create", "创建牌局", "迷宫 创建"),
            Button("lab_rules", "玩法规则", "迷宫 规则"),
        ]
    if not game.started:
        return _waiting_buttons(game, requester_id)
    return _playing_buttons(game, requester_id)


def _waiting_buttons(game: Game, requester_id: str) -> list[Button]:
    buttons = [Button("lab_join", "加入牌局", "迷宫 加入")]
    host = game.players[0] if game.players else None
    if host is not None and len(game.players) >= 2:
        buttons.append(
            Button("lab_start", "开始游戏", "迷宫 开始", only_for=host.user_id)
        )
    if game.find(requester_id) is not None:
        buttons.append(Button("lab_leave", "退出牌局", "迷宫 退出"))
    buttons.append(Button("lab_rules", "玩法规则", "迷宫 规则"))
    return buttons


def _playing_buttons(game: Game, requester_id: str) -> list[Button]:
    buttons: list[Button] = []
    # 私密目标：每人一个按钮，只有本人可点
    for index, player in enumerate(game.players):
        buttons.append(
            Button(
                f"lab_target_{index}",
                f"🎯 {game.label_of(player)}·目标",
                target_payload(player, game),
                only_for=player.user_id,
            )
        )

    current = game.current
    if current is not None:
        # 操作按钮始终按「当前回合玩家」生成，only_for 只允许他点击
        actor = current.user_id
        if game.phase == PHASE_PUSH:
            buttons.append(Button("lab_rotate", "转手牌", "迷宫 转", only_for=actor))
            for side in ("上", "下", "左", "右"):
                for line in PUSH_LINES:
                    buttons.append(
                        Button(
                            f"lab_push_{side}_{line}",
                            f"推{side}{line + 1}",
                            f"迷宫 推 {side} {line + 1}",
                            only_for=actor,
                        )
                    )
        elif game.phase == PHASE_MOVE:
            buttons.append(Button("lab_stop", "停手", "迷宫 停", only_for=actor))

    buttons.append(Button("lab_state", "棋盘状态", "迷宫 状态"))
    buttons.append(Button("lab_rules", "玩法规则", "迷宫 规则"))
    if game.phase == PHASE_ENDED:
        buttons = [b for b in buttons if not b.button_id.startswith("lab_target")]
    return buttons
