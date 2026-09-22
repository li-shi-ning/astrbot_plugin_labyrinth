"""牌局会话管理：解析指令、驱动规则引擎、拼装回复。"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from .engine import MAX_PLAYERS, PUSH_LINES, Game, GameError
from .render import (
    render_help,
    render_hint,
    render_menu,
    render_move,
    render_push,
    render_rules,
    render_table,
)
from .tiles import BOARD_SIZE

ACTION_ALIASES = {
    "创建": "create",
    "新建": "create",
    "开房": "create",
    "加入": "join",
    "参加": "join",
    "开始": "start",
    "开局": "start",
    "状态": "state",
    "棋盘": "state",
    "局势": "state",
    "目标": "target",
    "转": "rotate",
    "旋转": "rotate",
    "推": "push",
    "插入": "push",
    "走": "move",
    "移动": "move",
    "停": "stop",
    "不动": "stop",
    "原地": "stop",
    "退出": "leave",
    "离开": "leave",
    "解散": "dissolve",
    "结束": "dissolve",
    "帮助": "help",
    "菜单": "help",
    "指令": "help",
    "规则": "rules",
    "玩法": "rules",
}

SIDE_ALIASES = {
    "上": "上",
    "下": "下",
    "左": "左",
    "右": "右",
    "top": "上",
    "bottom": "下",
    "left": "左",
    "right": "右",
    "u": "上",
    "d": "下",
    "l": "左",
    "r": "右",
}


@dataclass
class Reply:
    """一次指令的结果：播报正文 + 牌桌 + 回合提示。"""

    text: str = ""
    table: str = ""
    hint: str = ""


class GameService:
    """按会话（群）维护若干牌局。"""

    def __init__(self) -> None:
        self.games: dict[str, Game] = {}
        self.locks: dict[str, asyncio.Lock] = {}

    def lock(self, session_id: str) -> asyncio.Lock:
        return self.locks.setdefault(session_id, asyncio.Lock())

    def game(self, session_id: str) -> Game | None:
        return self.games.get(session_id)

    def dispatch(self, session_id: str, user_id: str, name: str, text: str) -> Reply:
        """解析并执行一条指令。"""
        action, rest = self._parse_action(text)
        if action is None:
            return Reply(text=render_menu())
        if action == "help":
            return Reply(text=render_help())
        if action == "rules":
            return Reply(text=render_rules())
        if action == "create":
            return self._create(session_id, user_id, name)
        if action == "join":
            return self._join(session_id, user_id, name)
        if action == "start":
            return self._start(session_id, user_id)
        if action == "state":
            return self._board_reply(self._require(session_id))
        if action == "target":
            return self._target(session_id, user_id)
        if action == "rotate":
            return self._rotate(session_id, user_id)
        if action == "push":
            return self._push(session_id, user_id, rest)
        if action == "move":
            return self._move(session_id, user_id, rest)
        if action == "stop":
            return self._stop(session_id, user_id)
        if action == "leave":
            return self._leave(session_id, user_id, name)
        if action == "dissolve":
            return self._dissolve(session_id, user_id)
        raise GameError("无法识别的指令，发送「迷宫 帮助」查看用法")

    # ------------------------------------------------------------------
    def _create(self, session_id: str, user_id: str, name: str) -> Reply:
        if session_id in self.games:
            raise GameError("本群已经有一个牌局了，发送「迷宫 状态」查看")
        game = Game(session_id)
        game.add_player(user_id, name)
        self.games[session_id] = game
        return self._board_reply(game, f"🌀 {name} 创建了迷宫牌局")

    def _join(self, session_id: str, user_id: str, name: str) -> Reply:
        game = self._require(session_id)
        game.add_player(user_id, name)
        return self._board_reply(
            game, f"👋 {name} 加入（{len(game.players)}/{MAX_PLAYERS}）"
        )

    def _start(self, session_id: str, user_id: str) -> Reply:
        game = self._require(session_id)
        game.start(user_id)
        return self._board_reply(game)

    def _target(self, session_id: str, user_id: str) -> Reply:
        game = self._require(session_id)
        player = game.find(user_id)
        if player is None:
            raise GameError("你不在牌局中")
        return Reply(
            text=f"🎯 {game.label_of(player)} {player.name}，点下方属于你的「目标」按钮查看"
            "（只进你自己的输入框，勿发送）"
        )

    def _rotate(self, session_id: str, user_id: str) -> Reply:
        game = self._require(session_id)
        game.rotate_spare(user_id)
        return self._board_reply(game, "🔄 手牌已顺时针旋转 90°")

    def _push(self, session_id: str, user_id: str, rest: str) -> Reply:
        game = self._require(session_id)
        side, index = self._parse_push(rest)
        result = game.push(user_id, side, index)
        return self._board_reply(game, render_push(result))

    def _move(self, session_id: str, user_id: str, rest: str) -> Reply:
        game = self._require(session_id)
        row, col = self._parse_cell(rest)
        result = game.move(user_id, row, col)
        return self._board_reply(game, render_move(result))

    def _stop(self, session_id: str, user_id: str) -> Reply:
        game = self._require(session_id)
        result = game.stay(user_id)
        return self._board_reply(game, render_move(result))

    def _leave(self, session_id: str, user_id: str, name: str) -> Reply:
        game = self._require(session_id)
        game.remove_player(user_id)
        if not game.players:
            self.games.pop(session_id, None)
            return Reply(text="牌局已随最后一名玩家退出而解散。")
        return self._board_reply(game, f"👋 {name} 退出了牌局")

    def _dissolve(self, session_id: str, user_id: str) -> Reply:
        game = self._require(session_id)
        if game.players and game.players[0].user_id != user_id:
            raise GameError("只有房主可以解散牌局")
        self.games.pop(session_id, None)
        return Reply(text="🧹 牌局已解散。")

    # ------------------------------------------------------------------
    def _board_reply(self, game: Game, text: str = "") -> Reply:
        return Reply(text=text, table=render_table(game), hint=render_hint(game))

    def _require(self, session_id: str) -> Game:
        game = self.games.get(session_id)
        if game is None:
            raise GameError("本群还没有牌局，点击「创建牌局」开一局")
        return game

    @staticmethod
    def _parse_action(text: str) -> tuple[str | None, str]:
        text = text.strip()
        if not text:
            return None, ""
        for alias in sorted(ACTION_ALIASES, key=len, reverse=True):
            if text.startswith(alias):
                return ACTION_ALIASES[alias], text[len(alias) :].strip()
        return None, text

    @staticmethod
    def _parse_push(rest: str) -> tuple[str, int]:
        parts = [p for p in re.split(r"[\s,，]+", rest.strip()) if p]
        if len(parts) == 2 and parts[0].isdigit():
            parts = [parts[1], parts[0]]
        if len(parts) != 2:
            raise GameError("格式：迷宫 推 上 2（方向 + 2/4/6）")
        side = SIDE_ALIASES.get(parts[0].lower()) or SIDE_ALIASES.get(parts[0])
        if side is None:
            raise GameError("方向只能是 上/下/左/右")
        if not parts[1].isdigit():
            raise GameError("位置只能是 2、4、6")
        line = int(parts[1]) - 1
        if line not in PUSH_LINES:
            raise GameError("只能推第 2、4、6 行或列")
        return side, line

    @staticmethod
    def _parse_cell(rest: str) -> tuple[int, int]:
        parts = [p for p in re.split(r"[\s,，\-]+", rest.strip()) if p]
        if len(parts) != 2 or not all(p.isdigit() for p in parts):
            raise GameError("格式：迷宫 走 3 4（行 列，都从 1 开始）")
        row, col = int(parts[0]) - 1, int(parts[1]) - 1
        if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
            raise GameError("坐标要在 1-7 之间")
        return row, col
