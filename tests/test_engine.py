"""《Labyrinth》规则引擎测试。"""

from __future__ import annotations

import random

import pytest

from src.engine import (
    PHASE_ENDED,
    PHASE_MOVE,
    PHASE_PUSH,
    Game,
    GameError,
    Tile,
)
from src.tiles import BOARD_SIZE, FIXED_TILES, LOOSE_BAG, TREASURES, treasure_name


def make_game(players: int = 2, seed: int = 7, start: bool = True) -> Game:
    game = Game("g1", rng=random.Random(seed))
    for index in range(players):
        game.add_player(f"u{index + 1}", f"玩家{index + 1}")
    if start:
        game.start("u1")
    return game


def test_tile_openings_rotate() -> None:
    straight = Tile("straight")
    assert straight.openings() == {0, 2}
    straight.rotate()
    assert straight.openings() == {1, 3}

    corner = Tile("corner")
    assert corner.openings() == {0, 1}
    corner.rotate(2)
    assert corner.openings() == {2, 3}

    tee = Tile("t-shape")
    assert tee.openings() == {0, 1, 2}
    tee.rotate(3)
    assert tee.openings() == {0, 1, 3}


def test_board_setup() -> None:
    game = make_game(2)
    assert game.started and game.spare is not None
    fixed = sum(1 for row in game.grid for tile in row if tile.fixed)
    assert fixed == len(FIXED_TILES) == 16
    assert sum(1 for row in game.grid for tile in row if row is not None) == 49
    # 33 张可移动牌在棋盘上 + 1 张手牌
    assert sum(1 for row in game.grid for tile in row if not tile.fixed) == 33
    # 宝藏平均分牌
    assert all(len(p.treasures) == 12 for p in game.players)
    assert sorted(t for p in game.players for t in p.treasures) == sorted(TREASURES)
    # 起始角
    assert game.players[0].pos == (0, 0)
    assert game.players[1].pos == (6, 6)


def test_start_requires_host_and_players() -> None:
    one = make_game(1, start=False)
    with pytest.raises(GameError):
        one.start("u1")
    two = make_game(2, start=False)
    with pytest.raises(GameError):
        two.start("u2")


def test_push_shifts_line_and_recycles_spare() -> None:
    game = make_game(2)
    old_spare = game.spare
    first = game.grid[0][1]
    second = game.grid[1][1]
    old_bottom = game.grid[6][1]

    result = game.push("u1", "上", 1)

    assert result.inserted == (0, 1)
    assert result.ejected == (6, 1)
    assert game.grid[0][1] is old_spare
    assert game.grid[1][1] is first
    assert game.grid[2][1] is second
    assert game.spare is old_bottom
    assert game.phase == PHASE_MOVE


def test_cannot_push_back_immediately() -> None:
    game = make_game(2)
    game.push("u1", "上", 1)  # 把 (6,1) 推出
    game.stay("u1")  # 轮到 u2
    with pytest.raises(GameError):
        game.push("u2", "下", 1)  # 想从下面推回去
    game.push("u2", "上", 3)  # 换一条线可以


def test_only_push_lines_allowed() -> None:
    game = make_game(2)
    with pytest.raises(GameError):
        game.push("u1", "上", 0)
    with pytest.raises(GameError):
        game.push("u1", "上", 2)


def test_spare_can_be_rotated() -> None:
    game = make_game(2)
    before = game.spare.rotation
    game.rotate_spare("u1")
    assert game.spare.rotation == (before + 1) % 4
    with pytest.raises(GameError):
        game.rotate_spare("u2")


def test_pawn_pushed_off_board_moves_to_insertion() -> None:
    game = make_game(2)
    game.players[0].pos = (6, 1)  # 站在会被推出的位置
    game.push("u1", "上", 1)
    assert game.players[0].pos == (0, 1)


def test_pawns_in_line_shift_with_push() -> None:
    game = make_game(2)
    game.players[0].pos = (3, 1)
    game.players[1].pos = (3, 3)
    game.push("u1", "上", 1)
    assert game.players[0].pos == (4, 1)
    assert game.players[1].pos == (3, 3)  # 不在线上不动


def test_reachable_follows_corridors() -> None:
    game = make_game(2, start=False)
    game.grid = [
        [Tile("straight") for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)
    ]
    game.started = True
    game.players[0].pos = (0, 0)
    # 全是上下直通 → 只能在同一列来回
    assert game.reachable(game.players[0]) == {(row, 0) for row in range(BOARD_SIZE)}


def test_move_collects_target_then_needs_home() -> None:
    game = make_game(2)
    player = game.players[0]
    player.pos = (0, 0)
    player.treasures = ["Mouse", "Cat"]
    player.collected = 0
    # 放一个可以一步走到的老鼠
    game.grid = [
        [Tile("straight") for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)
    ]
    game.grid[1][0].treasure = "Mouse"
    game.grid[2][0].treasure = "Cat"
    game.phase = PHASE_MOVE

    result = game.move("u1", 1, 0)
    assert [t for _uid, t in result.collected] == ["Mouse"]
    assert player.collected == 1 and player.target == "Cat"

    game.turn_index = 0  # 测试里强制轮回自己
    game.phase = PHASE_MOVE
    game.move("u1", 2, 0)
    assert player.collected == 2 and player.target is None

    # 拿齐后回起点才算赢
    game.turn_index = 0
    game.phase = PHASE_MOVE
    result = game.move("u1", 0, 0)
    assert result.winner == "u1"
    assert game.phase == PHASE_ENDED


def test_cannot_move_when_not_reachable_or_wrong_phase() -> None:
    game = make_game(2)
    with pytest.raises(GameError):
        game.move("u1", 3, 3)  # 还没推牌
    game.push("u1", "上", 1)
    with pytest.raises(GameError):
        game.move("u1", 99, 99)
    with pytest.raises(GameError):
        game.move("u2", 3, 3)  # 不是他的回合


def test_full_random_game_keeps_invariants() -> None:
    game = make_game(3, seed=42)
    rng = random.Random(2024)
    for _ in range(400):
        if game.phase == PHASE_ENDED:
            break
        current = game.current
        assert current is not None
        if game.phase == PHASE_PUSH:
            if rng.random() < 0.5:
                game.rotate_spare(current.user_id)
            side = rng.choice(["上", "下", "左", "右"])
            index = rng.choice([1, 3, 5])
            try:
                game.push(current.user_id, side, index)
            except GameError:
                continue
        else:
            cells = sorted(game.reachable(current))
            row, col = rng.choice(cells)
            game.move(current.user_id, row, col)
        # 不变量
        for player in game.players:
            assert 0 <= player.pos[0] < BOARD_SIZE
            assert 0 <= player.pos[1] < BOARD_SIZE
            assert player.collected <= len(player.treasures)
    assert game.spare is not None
    for player in game.players:
        assert len(player.found) == player.collected


def test_all_treasures_have_names() -> None:
    for treasure in TREASURES:
        assert treasure_name(treasure) != treasure or treasure.isascii()
    assert len(LOOSE_BAG) == 34


def test_board_image_renders(tmp_path) -> None:
    """棋盘能渲染成 PNG（缺素材时用几何图形兜底）。"""
    pytest.importorskip("PIL")
    from src.board_image import render_board

    game = make_game(2, seed=5)
    game.push("u1", "上", 1)
    out = render_board(game, tmp_path / "board.png")
    assert out is not None and out.is_file()
    from PIL import Image

    with Image.open(out) as image:
        assert image.format == "PNG"
        assert image.width > 7 * 40 and image.height > 7 * 40
