"""《Labyrinth 疯狂迷宫》AstrBot 插件入口（QQ 官方机器人）。

本文件只做三件事：注册插件、把 QQ 官方群消息路由到
:class:`~src.service.GameService`、把回复连同 ``only_for`` 私密按钮发出。
规则逻辑在 :mod:`src.engine`，棋盘图片在 :mod:`src.board_image`。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, StarTools

try:  # AstrBot 以包形式加载插件时走相对导入
    from .src.board_image import render_board as render_board_image
    from .src.buttons import build_buttons
    from .src.qqofficial import (
        extract_group_context,
        is_qqofficial_event,
        send_group_media,
        send_group_message,
    )
    from .src.service import GameError, GameService, Reply
except ImportError:  # pragma: no cover - 兼容以顶层模块加载
    plugin_dir = Path(__file__).resolve().parent
    if str(plugin_dir) not in sys.path:
        sys.path.insert(0, str(plugin_dir))
    from src.board_image import render_board as render_board_image
    from src.buttons import build_buttons
    from src.qqofficial import (
        extract_group_context,
        is_qqofficial_event,
        send_group_media,
        send_group_message,
    )
    from src.service import GameError, GameService, Reply


PLUGIN_NAME = "astrbot_plugin_labyrinth"
COMMAND_NAMES = ("迷宫", "labyrinth", "疯狂迷宫")


class LabyrinthPlugin(Star):
    """QQ 官方机器人群聊《Labyrinth 疯狂迷宫》。"""

    def __init__(self, context: Context, config: Any = None):
        super().__init__(context)
        self.config = dict(config) if config else {}
        self.send_board_image = self._config_bool("board_image", True)
        self.board_dir = Path(StarTools.get_data_dir(PLUGIN_NAME))
        self.board_dir.mkdir(parents=True, exist_ok=True)
        self.board_font_path = (
            self._config_str("board_font_path", "") or self._default_font()
        )
        self.service = GameService()

    async def initialize(self) -> None:
        logger.info("[Labyrinth] initialized: board_image=%s", self.send_board_image)

    async def terminate(self) -> None:
        self.service.games.clear()
        self.service.locks.clear()
        logger.info("[Labyrinth] terminated")

    # ------------------------------------------------------------------
    # 指令入口
    # ------------------------------------------------------------------
    @filter.platform_adapter_type(
        filter.PlatformAdapterType.QQOFFICIAL
        | filter.PlatformAdapterType.QQOFFICIAL_WEBHOOK
    )
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    @filter.command("迷宫", alias={"labyrinth", "疯狂迷宫", "迷宫帮助", "迷宫菜单"})
    async def labyrinth(self, event: AstrMessageEvent):
        """《疯狂迷宫》主指令，按子指令分发。"""
        guard = self._guard(event)
        if guard:
            yield event.plain_result(guard)
            event.stop_event()
            return

        context = extract_group_context(event)
        if context is None:
            yield event.plain_result("无法识别 QQ 官方群聊身份，请稍后重试。")
            event.stop_event()
            return

        action_text = self._strip_prefix(event.message_str)
        is_admin = self._is_admin(event)
        lock = self.service.lock(context.group_openid)
        async with lock:
            try:
                reply = self.service.dispatch(
                    context.group_openid,
                    context.member_openid,
                    context.display_name,
                    action_text,
                    is_admin=is_admin,
                )
            except GameError as exc:
                reply = Reply(text=f"⚠️ {exc}")
            except Exception as exc:  # noqa: BLE001 - 单条指令失败不影响其他群
                logger.exception("[Labyrinth] dispatch failed: %s", exc)
                reply = Reply(text="迷宫处理失败，请稍后重试。")
            game = self.service.game(context.group_openid)
            buttons = build_buttons(game, context.member_openid)
            board_path = (
                self._render_board(game)
                if game is not None and game.started and self.send_board_image
                else None
            )

        # 1) 棋盘图片走富媒体（msg_type=7，不能带 Markdown/键盘）
        image_sent = False
        if board_path is not None:
            image_sent = await send_group_media(event, context, board_path)

        # 2) 文字 + 按钮走 Markdown 消息
        parts = [reply.text, None if image_sent else reply.table, reply.hint]
        body = "\n\n".join(part for part in parts if part)
        if not await send_group_message(event, context, body, buttons):
            yield event.plain_result(body)
        event.stop_event()

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------
    def _default_font(self) -> str:
        """优先用 AstrBot 自带的 /AstrBot/data/font.ttf。"""
        candidate = self.board_dir.parent.parent / "font.ttf"
        return str(candidate) if candidate.is_file() else ""

    def _render_board(self, game) -> Path | None:
        """把棋盘渲染成本地 PNG，失败返回 None（会退回文字牌桌）。"""
        try:
            return render_board_image(
                game,
                self.board_dir / "board.png",
                font_path=self.board_font_path or None,
            )
        except Exception as exc:  # noqa: BLE001 - 渲染失败不应影响出牌
            logger.warning("[Labyrinth] render board failed: %s", exc)
            return None

    @staticmethod
    def _is_admin(event: AstrMessageEvent) -> bool:
        """判断发送者是否 AstrBot 管理员（管理员也能解散牌局）。"""
        checker = getattr(event, "is_admin", None)
        if callable(checker):
            try:
                return bool(checker())
            except Exception:  # noqa: BLE001 - 不同适配器实现不同
                return False
        return bool(checker)

    def _guard(self, event: AstrMessageEvent) -> str | None:
        platform_name = (
            event.get_platform_name() if hasattr(event, "get_platform_name") else ""
        )
        if platform_name not in {"qq_official", "qq_official_webhook"} and not (
            is_qqofficial_event(event)
        ):
            return "疯狂迷宫目前仅支持 QQ 官方机器人群聊。"
        return None

    @staticmethod
    def _strip_prefix(raw: str) -> str:
        text = raw.strip()
        for prefix in COMMAND_NAMES:
            if text.lower().startswith(prefix.lower()):
                return text[len(prefix) :].strip()
        return text

    def _config_str(self, key: str, default: str) -> str:
        value = (
            self.config.get(key, default) if hasattr(self.config, "get") else default
        )
        text = str(value).strip() if value else ""
        return text or default

    def _config_bool(self, key: str, default: bool) -> bool:
        value = (
            self.config.get(key, default) if hasattr(self.config, "get") else default
        )
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on", "是"}
        return bool(value)
