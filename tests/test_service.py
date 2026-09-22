"""指令解析与会话管理测试。"""

from __future__ import annotations

import pytest

from src.buttons import build_buttons
from src.engine import PHASE_MOVE, PHASE_PUSH, GameError
from src.render import target_payload
from src.service import GameService
from src.tiles import cell_name


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
    """上下推要选列字母，左右推要选行号；只能推 b/d/f 与 2/4/6。"""
    service = make_service()
    game = service.game("g1")
    assert game is not None
    game.start("u1")
    assert service._parse_push("上 b") == ("上", 1)
    assert service._parse_push("下 d") == ("下", 3)
    assert service._parse_push("左 2") == ("左", 5)
    assert service._parse_push("右 6") == ("右", 1)
    assert service._parse_push("b 上") == ("上", 1)
    assert service._parse_push("↑ f") == ("上", 5)
    with pytest.raises(GameError):
        service._parse_push("上 a")  # a 列推不了
    with pytest.raises(GameError):
        service._parse_push("左 3")  # 第 3 行推不了
    with pytest.raises(GameError):
        service._parse_push("上")


def test_parse_cell() -> None:
    """列 a-g 从左到右，行 1-7 从下到上。"""
    assert GameService._parse_cell("c3") == (4, 2)
    assert GameService._parse_cell("C3") == (4, 2)
    assert GameService._parse_cell("3c") == (4, 2)
    assert GameService._parse_cell("c 3") == (4, 2)
    assert GameService._parse_cell("a1") == (6, 0)
    assert GameService._parse_cell("g7") == (0, 6)
    assert GameService._parse_cell("d4") == (3, 3)
    with pytest.raises(GameError):
        GameService._parse_cell("h3")
    with pytest.raises(GameError):
        GameService._parse_cell("c8")
    with pytest.raises(GameError):
        GameService._parse_cell("3")


def test_push_then_move_flow() -> None:
    service = make_service()
    game = service.game("g1")
    assert game is not None
    game.start("u1")
    text = flat(service.dispatch("g1", "u1", "甲", "推 上 b"))
    assert "推入" in text and game.phase == PHASE_MOVE
    # 越界坐标一定被拒
    with pytest.raises(GameError):
        service.dispatch("g1", "u1", "甲", "走 h1")
    # 走到一个真实可达格（棋盘随机，所以从引擎里取）
    target = sorted(game.reachable(game.players[0]))[-1]
    assert "移动完成" in flat(
        service.dispatch("g1", "u1", "甲", f"走 {cell_name(*target)}")
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


def test_push_buttons_layout_one_column_per_side() -> None:
    """推牌按钮排成 3 行 4 列，一列一边。"""
    from src.buttons import build_buttons
    from src.qqofficial import build_keyboard

    service = make_service()
    game = service.game("g1")
    assert game is not None
    game.start("u1")
    rows = build_keyboard(build_buttons(game, "u1"))["content"]["rows"]
    labels = [[b["render_data"]["label"] for b in r["buttons"]] for r in rows]
    push_rows = [r for r in labels if any(x.startswith("推") for x in r)]
    assert len(push_rows) == 3
    assert all(len(r) == 4 for r in push_rows)
    # 每一列固定一个方向：上 / 下 / 左 / 右
    for column, side in enumerate(["上", "下", "左", "右"]):
        assert [row[column][1] for row in push_rows] == [side] * 3
    # 上下按列字母 b/d/f，左右按行号 2/4/6
    for column in (0, 1):
        assert [row[column][2:] for row in push_rows] == ["b", "d", "f"]
    for column in (2, 3):
        assert [row[column][2:] for row in push_rows] == ["2", "4", "6"]


def test_move_phase_has_single_move_button() -> None:
    """移动阶段只给一个「移动」按钮，点完补成「迷宫 走 」。"""
    from src.buttons import build_buttons
    from src.engine import PHASE_MOVE, Tile
    from src.qqofficial import build_keyboard
    from src.tiles import BOARD_SIZE

    service = make_service()
    game = service.game("g1")
    assert game is not None
    game.start("u1")
    game.grid = [
        [Tile("straight") for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)
    ]
    game.players[0].pos = (0, 0)
    game.phase = PHASE_MOVE

    rows = build_keyboard(build_buttons(game, "u1"))["content"]["rows"]
    items = [
        (b["render_data"]["label"], b["action"]["data"])
        for r in rows
        for b in r["buttons"]
    ]
    move_buttons = [item for item in items if item[0] == "移动"]
    assert len(move_buttons) == 1
    assert move_buttons[0][1] == "迷宫 走 "  # 只差坐标
    assert "停手" in [label for label, _ in items]
    assert not [label for label, _ in items if label.startswith("走")]


def test_move_rejects_unreachable_cell() -> None:
    """坐标合法但走不到时,引擎会拒绝。"""
    from src.engine import PHASE_MOVE, Tile
    from src.tiles import BOARD_SIZE, cell_name

    service = make_service()
    game = service.game("g1")
    assert game is not None
    game.start("u1")
    game.grid = [
        [Tile("straight") for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)
    ]
    game.players[0].pos = (3, 0)  # d4
    game.phase = PHASE_MOVE

    # 同一列可达
    assert "移动完成" in flat(service.dispatch("g1", "u1", "甲", "走 a1"))
    # 换一个人、重新摆放：邻列走不到（全是上下直路）
    game.players[0].pos = (0, 0)
    game.turn_index = 0
    game.phase = PHASE_MOVE
    assert cell_name(0, 0) == "a7"
    with pytest.raises(GameError):
        service.dispatch("g1", "u1", "甲", "走 b6")


def test_game_end_destroys_room() -> None:
    """对局结束后播报胜利玩家并销毁房间。"""
    service = make_service()
    game = service.game("g1")
    assert game is not None
    game.start("u1")
    player = game.players[0]
    player.treasures = ["Rat"]
    player.collected = 1
    player.pos = player.start
    game.turn_index = 0
    game.phase = PHASE_MOVE

    reply = service.dispatch("g1", "u1", "甲", f"走 {cell_name(*player.start)}")
    assert "获胜" in reply.text and "甲" in reply.text
    assert "房间已销毁" in reply.text
    assert service.game("g1") is None  # 房间已销毁
    assert reply.board is not None  # 但仍能画最后一张棋盘


def test_admin_can_dissolve_room() -> None:
    """管理员和房主都能解散，包括对局进行中。"""
    service = make_service()
    game = service.game("g1")
    assert game is not None
    game.start("u1")
    # 非房主、非管理员不行
    with pytest.raises(GameError):
        service.dispatch("g1", "u2", "乙", "解散")
    # 管理员可以
    assert "解散" in flat(service.dispatch("g1", "u9", "路人", "解散", is_admin=True))
    assert service.game("g1") is None

    # 房主也可以
    service.dispatch("g1", "u1", "甲", "创建")
    service.dispatch("g1", "u2", "乙", "加入")
    service.dispatch("g1", "u1", "甲", "开始")
    assert "解散" in flat(service.dispatch("g1", "u1", "甲", "解散"))
    assert service.game("g1") is None


def test_waiting_room_hint_is_not_turn_prompt() -> None:
    """未开局时不要显示「轮到你推牌」。"""
    service = GameService()
    reply = service.dispatch("g1", "u1", "甲", "创建")
    text = flat(reply)
    assert "等待房主点击「开始游戏」" in text
    assert "推牌" not in text
