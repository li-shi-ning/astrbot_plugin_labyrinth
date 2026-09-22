"""《Labyrinth 疯狂迷宫》规则引擎（纯逻辑，不依赖 AstrBot）。"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field

from .tiles import (
    BASE_OPENINGS,
    BOARD_SIZE,
    DIRS,
    FIXED_TILES,
    LOOSE_BAG,
    OPPOSITE,
    START_POSITIONS,
    TREASURES,
)

PHASE_PUSH = "push"  # 等待推牌（含旋转手牌）
PHASE_MOVE = "move"  # 推完了，可选移动或停手
PHASE_ENDED = "ended"

MIN_PLAYERS = 2
MAX_PLAYERS = 4
PUSH_LINES = (1, 3, 5)  # 可推的行/列（0 基）
SIDES = ("上", "下", "左", "右")


class GameError(Exception):
    """玩家操作不合法时抛出，异常信息可直接展示给玩家。"""


@dataclass
class Tile:
    """一张迷宫牌。``rotation`` 为顺时针 90° 的次数（0-3）。"""

    kind: str
    rotation: int = 0
    treasure: str | None = None
    fixed: bool = False

    def openings(self) -> set[int]:
        """当前出口的方向集合。"""
        return {(d + self.rotation) % 4 for d in BASE_OPENINGS[self.kind]}

    def opens_to(self, direction: int) -> bool:
        return direction in self.openings()

    def rotate(self, steps: int = 1) -> None:
        self.rotation = (self.rotation + steps) % 4


@dataclass
class Player:
    """一名玩家。"""

    user_id: str
    name: str
    color: str
    start: tuple[int, int]
    pos: tuple[int, int] = (0, 0)
    treasures: list[str] = field(default_factory=list)
    collected: int = 0

    @property
    def target(self) -> str | None:
        """当前要找的宝藏；全部找齐后为 ``None``（此时要回家）。"""
        if self.collected < len(self.treasures):
            return self.treasures[self.collected]
        return None

    @property
    def all_collected(self) -> bool:
        return self.collected >= len(self.treasures)

    @property
    def found(self) -> list[str]:
        return self.treasures[: self.collected]


@dataclass
class PushResult:
    """一次推牌的结果。"""

    inserted: tuple[int, int]
    ejected: tuple[int, int]
    side: str
    index: int
    rotated: int
    collected: list[tuple[str, str]] = field(default_factory=list)
    winner: str | None = None


@dataclass
class MoveResult:
    """一次移动/停手的结果。"""

    stayed: bool = False
    collected: list[tuple[str, str]] = field(default_factory=list)
    winner: str | None = None


class Game:
    """一局《Labyrinth》。"""

    def __init__(self, session_id: str, rng: random.Random | None = None) -> None:
        self.session_id = session_id
        self.rng = rng or random.Random()
        self.players: list[Player] = []
        self.grid: list[list[Tile]] = []
        self.spare: Tile | None = None
        self.turn_index = 0
        self.phase = PHASE_PUSH
        self.started = False
        self.winner: str | None = None
        self.last_ejected: tuple[int, int] | None = None

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    @property
    def current(self) -> Player | None:
        if not self.players:
            return None
        return self.players[self.turn_index]

    def find(self, user_id: str) -> Player | None:
        return next((p for p in self.players if p.user_id == user_id), None)

    def find_by_label(self, label: str) -> Player | None:
        label = label.upper()
        for index, player in enumerate(self.players):
            if chr(ord("A") + index) == label:
                return player
        return None

    def label_of(self, player: Player) -> str:
        return chr(ord("A") + self.players.index(player))

    def tile(self, row: int, col: int) -> Tile:
        return self.grid[row][col]

    def players_at(self, row: int, col: int) -> list[Player]:
        return [p for p in self.players if p.pos == (row, col)]

    # ------------------------------------------------------------------
    # 房间 / 开局
    # ------------------------------------------------------------------
    def add_player(self, user_id: str, name: str) -> Player:
        if self.started:
            raise GameError("本局已经开始了，无法加入")
        if len(self.players) >= MAX_PLAYERS:
            raise GameError(f"房间已满（最多 {MAX_PLAYERS} 人）")
        if self.find(user_id):
            raise GameError("你已经在房间里了")
        start, color = START_POSITIONS[len(self.players)]
        player = Player(user_id=user_id, name=name, color=color, start=start)
        player.pos = start
        self.players.append(player)
        return player

    def remove_player(self, user_id: str) -> None:
        if self.started:
            raise GameError("对局进行中无法退出，请让房主解散牌局")
        player = self.find(user_id)
        if player is None:
            raise GameError("你不在房间里")
        self.players.remove(player)
        for index, remaining in enumerate(self.players):
            _, remaining.color = START_POSITIONS[index]
            remaining.start = START_POSITIONS[index][0]
            remaining.pos = remaining.start

    def start(self, user_id: str) -> None:
        if not self.players:
            raise GameError("房间里还没有玩家")
        if self.players[0].user_id != user_id:
            raise GameError("只有房主可以开始游戏")
        if len(self.players) < MIN_PLAYERS:
            raise GameError(f"至少需要 {MIN_PLAYERS} 名玩家才能开始")
        if self.started:
            raise GameError("本局已经开始了")

        # 1. 固定牌
        self.grid = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        for (row, col), (kind, rotation, treasure, _home) in FIXED_TILES.items():
            self.grid[row][col] = Tile(kind, rotation, treasure, fixed=True)

        # 2. 可移动牌填满 33 个空格，剩 1 张做手牌
        bag = [
            Tile(kind, self.rng.randrange(4), treasure) for kind, treasure in LOOSE_BAG
        ]
        self.rng.shuffle(bag)
        self.spare = bag.pop()
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if self.grid[row][col] is None:
                    self.grid[row][col] = bag.pop()

        # 3. 发宝藏
        deck = list(TREASURES)
        self.rng.shuffle(deck)
        per_player = len(deck) // len(self.players)
        for index, player in enumerate(self.players):
            player.treasures = deck[index * per_player : (index + 1) * per_player]
            player.collected = 0
            player.pos = player.start

        self.started = True
        self.turn_index = 0
        self.phase = PHASE_PUSH
        self.winner = None
        self.last_ejected = None

    # ------------------------------------------------------------------
    # 回合：推牌
    # ------------------------------------------------------------------
    def rotate_spare(self, user_id: str) -> None:
        if self.phase != PHASE_PUSH:
            raise GameError("推牌阶段才能旋转手牌")
        self._require_current(user_id)
        if self.spare is None:
            raise GameError("当前没有手牌")
        self.spare.rotate()

    def push(self, user_id: str, side: str, index: int) -> PushResult:
        if self.phase != PHASE_PUSH:
            raise GameError("这一手已经推过了，请移动或停手")
        self._require_current(user_id)
        if self.spare is None:
            raise GameError("当前没有手牌")
        if side not in SIDES:
            raise GameError("推牌方向只能是 上/下/左/右")
        if index not in PUSH_LINES:
            raise GameError("只能推第 2、4、6 行或列")

        insertion, ejected = self._push_cells(side, index)
        if self.last_ejected == insertion:
            raise GameError("不能把上一手刚推出的牌原路推回去")
        if self.grid[insertion[0]][insertion[1]].fixed:
            raise GameError("这里是固定牌，推不动")

        rotated = self.spare.rotation
        ejected_tile = self._shift(side, index, self.spare)
        self.spare = ejected_tile
        self.last_ejected = ejected

        collected = self._sync_treasures()
        winner = self._check_winner()
        if winner is None:
            self.phase = PHASE_MOVE
        return PushResult(
            inserted=insertion,
            ejected=ejected,
            side=side,
            index=index,
            rotated=rotated,
            collected=collected,
            winner=winner,
        )

    def _push_cells(
        self, side: str, index: int
    ) -> tuple[tuple[int, int], tuple[int, int]]:
        """返回 (插入格, 被推出的格)。"""
        last = BOARD_SIZE - 1
        if side == "上":
            return (0, index), (last, index)
        if side == "下":
            return (last, index), (0, index)
        if side == "左":
            return (index, 0), (index, last)
        return (index, last), (index, 0)

    def _shift(self, side: str, index: int, spare: Tile) -> Tile:
        """把 ``spare`` 插入并整体位移，返回被推出的牌。"""
        last = BOARD_SIZE - 1
        if side == "上":
            ejected = self.grid[last][index]
            for row in range(last, 0, -1):
                self.grid[row][index] = self.grid[row - 1][index]
            self.grid[0][index] = spare
        elif side == "下":
            ejected = self.grid[0][index]
            for row in range(last):
                self.grid[row][index] = self.grid[row + 1][index]
            self.grid[last][index] = spare
        elif side == "左":
            ejected = self.grid[index][last]
            for col in range(last, 0, -1):
                self.grid[index][col] = self.grid[index][col - 1]
            self.grid[index][0] = spare
        else:  # 右
            ejected = self.grid[index][0]
            for col in range(last):
                self.grid[index][col] = self.grid[index][col + 1]
            self.grid[index][last] = spare

        self._move_pawns(side, index, ejected_cell=self._push_cells(side, index)[1])
        return ejected

    def _move_pawns(self, side: str, index: int, ejected_cell: tuple[int, int]) -> None:
        """推牌时带动整条线上的棋子；被推出棋盘的回插入格。"""
        insertion, _ = self._push_cells(side, index)
        delta = {"上": (1, 0), "下": (-1, 0), "左": (0, 1), "右": (0, -1)}[side]
        for player in self.players:
            row, col = player.pos
            in_line = col == index if side in ("上", "下") else row == index
            if not in_line:
                continue
            if player.pos == ejected_cell:
                player.pos = insertion
            else:
                player.pos = (row + delta[0], col + delta[1])

    # ------------------------------------------------------------------
    # 回合：移动
    # ------------------------------------------------------------------
    def reachable(self, player: Player) -> set[tuple[int, int]]:
        """从当前位置沿通路可达的所有格子（含原地）。"""
        seen = {player.pos}
        queue = deque([player.pos])
        while queue:
            row, col = queue.popleft()
            tile = self.grid[row][col]
            for direction in tile.openings():
                dr, dc = DIRS[direction]
                nr, nc = row + dr, col + dc
                if not (0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE):
                    continue
                if (nr, nc) in seen:
                    continue
                neighbor = self.grid[nr][nc]
                if not neighbor.opens_to(OPPOSITE[direction]):
                    continue
                seen.add((nr, nc))
                queue.append((nr, nc))
        return seen

    def move(self, user_id: str, row: int, col: int) -> MoveResult:
        if self.phase != PHASE_MOVE:
            raise GameError("请先推牌，再移动")
        current = self._require_current(user_id)
        if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
            raise GameError("坐标要在 1-7 之间")
        if (row, col) not in self.reachable(current):
            raise GameError("沿通路走不到这一格")
        current.pos = (row, col)
        collected = self._sync_treasures()
        winner = self._check_winner()
        if winner is None:
            self._finish_turn()
        return MoveResult(collected=collected, winner=winner)

    def stay(self, user_id: str) -> MoveResult:
        if self.phase != PHASE_MOVE:
            raise GameError("请先推牌")
        self._require_current(user_id)
        self._finish_turn()
        return MoveResult(stayed=True)

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _sync_treasures(self) -> list[tuple[str, str]]:
        """结算所有玩家脚下的宝藏（推牌也可能把棋子送上去）。"""
        collected: list[tuple[str, str]] = []
        for player in self.players:
            target = player.target
            if target is None:
                continue
            row, col = player.pos
            if self.grid[row][col].treasure == target:
                player.collected += 1
                collected.append((player.user_id, target))
        return collected

    def _check_winner(self) -> str | None:
        for player in self.players:
            if player.all_collected and player.pos == player.start:
                self.winner = player.user_id
                self.phase = PHASE_ENDED
                return player.user_id
        return None

    def _finish_turn(self) -> None:
        self.turn_index = (self.turn_index + 1) % len(self.players)
        self.phase = PHASE_PUSH

    def _require_current(self, user_id: str) -> Player:
        current = self.current
        if current is None:
            raise GameError("当前没有进行中的回合")
        if current.user_id != user_id:
            raise GameError(f"现在轮到 {self.label_of(current)}({current.name})")
        return current
