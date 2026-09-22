"""棋盘渲染：素材合成与旋转验证。"""

from __future__ import annotations

import random

import pytest

pytest.importorskip("PIL")

from PIL import Image, ImageDraw  # noqa: E402

from src import board_image  # noqa: E402
from src.engine import Game, Tile  # noqa: E402


def make_tile_assets(tmp_path):
    """造一张 corner 底图：上边红、右边蓝（透明背景）。"""
    tile_dir = tmp_path / "tiles"
    tile_dir.mkdir()
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 63, 15], fill=(255, 0, 0, 255))  # 上
    draw.rectangle([48, 0, 63, 63], fill=(0, 0, 255, 255))  # 右
    image.save(tile_dir / "corner.png")
    return tile_dir


def test_tile_asset_is_pasted_and_rotated_clockwise(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(board_image, "TILE_DIR", make_tile_assets(tmp_path))

    base0 = board_image._tile_base(Tile("corner", 0))
    assert base0.getpixel((32, 4))[0] > 200  # 上边是红的
    assert base0.getpixel((60, 32))[2] > 200  # 右边是蓝的

    base1 = board_image._tile_base(Tile("corner", 1))  # 顺时针 90°
    assert base1.getpixel((60, 32))[0] > 200  # 红边转到右边
    assert base1.getpixel((32, 60))[2] > 200  # 蓝边转到下边


def test_falls_back_to_procedural_when_asset_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(board_image, "TILE_DIR", tmp_path / "empty")
    base = board_image._tile_base(Tile("t-shape", 0))
    # 程序化底图：墙用 WALL 色，通道用 FLOOR 色
    assert base.getpixel((32, 4)) == board_image.FLOOR  # 上口
    assert base.getpixel((4, 32)) == board_image.WALL  # 左边是墙


def test_treasure_icon_and_pawn_assets(tmp_path, monkeypatch) -> None:
    treasure_dir = tmp_path / "treasures"
    treasure_dir.mkdir()
    Image.new("RGBA", (64, 64), (0, 255, 0, 255)).save(treasure_dir / "Mouse.png")
    pawn_dir = tmp_path / "pawns"
    pawn_dir.mkdir()
    Image.new("RGBA", (64, 64), (255, 0, 255, 255)).save(pawn_dir / "yellow.png")
    monkeypatch.setattr(board_image, "TREASURE_DIR", treasure_dir)
    monkeypatch.setattr(board_image, "PAWN_DIR", pawn_dir)

    game = Game("g", rng=random.Random(1))
    game.add_player("u1", "四")
    game.add_player("u2", "默然")
    game.start("u1")
    game.players[0].pos = (0, 0)
    out = board_image.render_board(game, tmp_path / "board.png")
    assert out is not None

    tile = board_image._render_tile(Tile("corner", 0, "Mouse"))
    assert tile.getpixel((32, 32))[1] > 200  # 中央被绿色宝藏图标覆盖
