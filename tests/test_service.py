"""指令解析与会话管理测试。"""

from __future__ import annotations

import pytest

from src.buttons import build_buttons
from src.engine import PHASE_MOVE, PHASE_PUSH, GameError
from src.render import target_payload
from src.service import GameService


def flat(reply) -> str:
    return "\n\n".join(p for p in (reply.text, reply.table, reply.hint) if p)


def make_service() -> GameService:
    service = GameService()
    service.dispatch("g1", "u1", "甲", "创建")
    service.dispatch("g1", "u2", "乙", "加入")
    return service


def test_parse_action() -> None:
    assert GameService._parse_action("创建") == ("create", "")
    assert GameService._parse_action("推 上 2") == ("push", "上 2")
    assert GameService._parse_action("走 3 4") == ("move", "3 4")
    assert GameService._parse_action("停") == ("stop", "")
    assert GameService._parse_action("规则") == ("rules", "")
    assert GameService._parse_action("随便说点什么")[0] is None


def test_create_join_start_flow() -> None:
    service = GameService()
    assert "创建了迷宫牌局" in flat(service.dispatch("g1", "u1", "甲", "创建"))
    assert "加入" in flat(service.dispatch("g1", "u2", "乙", "加入"))
    with pytest.raises(GameError):
        service.dispatch("g1", "u2", "乙", "开始")
    text = flat(service.dispatch("g1", "u1", "甲", "开始"))
    assert "推" in text and "手牌" in text
    game = service.game("g1")
    assert game is not None and game.started


def test_no_game_hints_create() -> None:
    service = GameService()
    with pytest.raises(GameError):
        service.dispatch("g1", "u1", "甲", "状态")
    assert "迷宫" in flat(service.dispatch("g1", "u1", "甲", "帮助"))
    assert "迷宫" in flat(service.dispatch("g1", "u1", "甲", ""))


def test_parse_push_variants() -> None:
    service = make_service()
    game = service.game("g1")
    assert game is not None
    game.start("u1")
    assert service._parse_push("上 2") == ("上", 1)
    assert service._parse_push("2 上") == ("上", 1)
    assert service._parse_push("下 6") == ("下", 5)
    assert service._parse_push("left 4") == ("左", 3)
    with pytest.raises(GameError):
        service._parse_push("上 3")
    with pytest.raises(GameError):
        service._parse_push("左 1")
    with pytest.raises(GameError):
        service._parse_push("上")


def test_parse_cell() -> None:
    assert GameService._parse_cell("3 4") == (2, 3)
    assert GameService._parse_cell("1-1") == (0, 0)
    assert GameService._parse_cell("7,7") == (6, 6)
    with pytest.raises(GameError):
        GameService._parse_cell("0 1")
    with pytest.raises(GameError):
        GameService._parse_cell("8 1")
    with pytest.raises(GameError):
        GameService._parse_cell("3")


def test_push_then_move_flow() -> None:
    service = make_service()
    game = service.game("g1")
    assert game is not None
    game.start("u1")
    text = flat(service.dispatch("g1", "u1", "甲", "推 上 2"))
    assert "推入" in text and game.phase == PHASE_MOVE
    # 越界坐标一定被拒
    with pytest.raises(GameError):
        service.dispatch("g1", "u1", "甲", "走 0 1")
    # 走到一个真实可达格（棋盘随机，所以从引擎里取）
    target = sorted(game.reachable(game.players[0]))[-1]
    assert "移动完成" in flat(
        service.dispatch("g1", "u1", "甲", f"走 {target[0] + 1} {target[1] + 1}")
    )
    assert game.phase == PHASE_PUSH
    assert game.current is not None and game.current.user_id == "u2"


def test_target_is_private() -> None:
    service = make_service()
    game = service.game("g1")
    assert game is not None
    game.start("u1")
    text = flat(service.dispatch("g1", "u1", "甲", "目标"))
    assert "目标" in text
    payload = target_payload(game.players[0], game)
    assert game.players[0].treasures[0] in payload or "目标" in payload
    assert "请勿发送" in payload


def test_buttons_follow_current_player() -> None:
    service = make_service()
    game = service.game("g1")
    assert game is not None
    game.start("u1")
    game.push("u1", "上", 1)
    game.stay("u1")  # 轮到 u2
    buttons = build_buttons(game, "u1")  # 消息由 u1 触发
    push_buttons = [b for b in buttons if b.label.startswith("推")]
    assert push_buttons, "当前玩家必须有推牌按钮"
    assert all(b.only_for == "u2" for b in push_buttons)
    assert all(
        "请勿发送" in b.data or "目标" in b.data for b in buttons if "目标" in b.label
    )


def test_dissolve_requires_host() -> None:
    service = make_service()
    with pytest.raises(GameError):
        service.dispatch("g1", "u2", "乙", "解散")
    assert "解散" in flat(service.dispatch("g1", "u1", "甲", "解散"))
    assert service.game("g1") is None


def test_target_payload_uses_emoji() -> None:
    """私密目标提示是 emoji + 中文名。"""
    service = make_service()
    game = service.game("g1")
    assert game is not None
    game.start("u1")
    player = game.players[0]
    payload = target_payload(player, game)
    assert payload.startswith(f"🎯 {game.label_of(player)} 目标：")
    assert "（看完请勿发送）" in payload
    from src.tiles import TREASURE_EMOJI

    assert TREASURE_EMOJI[player.treasures[0]] in payload
