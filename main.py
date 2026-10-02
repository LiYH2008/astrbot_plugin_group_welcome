from __future__ import annotations

"""AstrBot 群迎新与新好友欢迎插件。

支持：
- OneBot v11 (aiocqhttp) 的 group_increase 通知事件
- OneBot v11 (aiocqhttp) 的 friend_add / friend 请求事件
- AstrBot 可转换为 AstrMessageEvent 的其它平台私聊事件
"""

import json
import re
import time
from collections.abc import Mapping
from typing import Any

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register


@register(
    "astrbot_plugin_group_welcome",
    "LiYH",
    "群聊入群 @ 欢迎与新好友自动欢迎，支持 OneBot v11 (aiocqhttp)",
    "1.0.0",
)
class GroupWelcomePlugin(Star):
    """处理入群和新好友事件。"""

    def __init__(self, context: Context, config: AstrBotConfig | None = None):
        super().__init__(context)
        self.config = config
        self._friend_greeted_at: dict[str, float] = {}

    def _config_get(self, key: str, default: Any) -> Any:
        """兼容 AstrBotConfig 和普通 dict，避免旧版本启动时配置为空。"""
        if self.config is None:
            return default
        try:
            return self.config.get(key, default)
        except Exception:
            try:
                return self.config[key]
            except Exception:
                return default

    @staticmethod
    def _raw_event(event: AstrMessageEvent) -> Any:
        """取得 AstrBot 包装的 OneBot 原始事件。"""
        message_obj = getattr(event, "message_obj", None)
        raw = getattr(message_obj, "raw_message", None)
        if raw is not None:
            if isinstance(raw, str):
                try:
                    return json.loads(raw)
                except (TypeError, ValueError):
                    return raw
            return raw
        raw = getattr(event, "raw_message", None)
        if raw is not None:
            if isinstance(raw, str):
                try:
                    return json.loads(raw)
                except (TypeError, ValueError):
                    return raw
            return raw
        # 某些适配器直接把字典放在 message_obj 上。
        if isinstance(message_obj, Mapping):
            return message_obj
        return {}

    @staticmethod
    def _get(raw: Any, key: str, default: Any = None) -> Any:
        if isinstance(raw, Mapping):
            return raw.get(key, default)
        return getattr(raw, key, default)

    @staticmethod
    def _normalise_groups(value: Any) -> set[str]:
        """把 WebUI 的 list/string 配置统一为群号集合。"""
        if value is None:
            return set()
        values = value if isinstance(value, (list, tuple, set)) else [value]
        groups: set[str] = set()
        for item in values:
            if item is None:
                continue
            # 允许在一个输入框中填写：123,456 或每行一个群号。
            for group_id in re.split(r"[,，;；\s]+", str(item)):
                group_id = group_id.strip()
                if group_id and group_id.isdigit():
                    groups.add(group_id)
        return groups

    def _allowed_groups(self) -> set[str]:
        return self._normalise_groups(self._config_get("group_ids", []))

    def _welcome_text(self) -> str:
        return str(
            self._config_get(
                "welcome_text",
                "欢迎加入本群！请先阅读群公告，祝大家聊天愉快～",
            )
            or ""
        ).strip()

    def _friend_text(self) -> str:
        return str(
            self._config_get(
                "friend_text",
                "你好，已成功添加好友！很高兴认识你～",
            )
            or ""
        ).strip()

    @staticmethod
    def _is_onebot_event(event: AstrMessageEvent, raw: Any) -> bool:
        """判断是否为 OneBot/aiocqhttp，名称判断保留对不同版本的兼容。"""
        platform = str(
            getattr(event, "platform_name", None)
            or getattr(event, "platform", None)
            or ""
        ).lower()
        if "aiocqhttp" in platform or "onebot" in platform:
            return True
        post_type = str(GroupWelcomePlugin._get(raw, "post_type", "")).lower()
        # OneBot 原始事件一定带 post_type，避免依赖平台类的导入路径。
        return post_type in {"notice", "request", "message"} and (
            GroupWelcomePlugin._get(raw, "self_id") is not None
        )

    async def _send_onebot_group_welcome(
        self, event: AstrMessageEvent, group_id: str, user_id: str, text: str
    ) -> bool:
        """通过 OneBot API 发送真正的 @ 消息。"""
        if not text or not getattr(event, "bot", None):
            return False
        try:
            await event.bot.api.call_action(
                "send_group_msg",
                group_id=int(group_id),
                message=[
                    {"type": "at", "data": {"qq": str(user_id)}},
                    {"type": "text", "data": {"text": f" {text}"}},
                ],
            )
            return True
        except Exception as exc:
            logger.warning(f"发送 OneBot 入群欢迎失败 group={group_id} user={user_id}: {exc}")
            return False

    async def _send_onebot_private_welcome(
        self, event: AstrMessageEvent, user_id: str, text: str
    ) -> bool:
        """通过 OneBot API 给新好友发送私聊欢迎。"""
        if not text or not user_id or not getattr(event, "bot", None):
            return False
        try:
            await event.bot.api.call_action(
                "send_private_msg",
                user_id=int(user_id),
                message=[{"type": "text", "data": {"text": text}}],
            )
            return True
        except Exception as exc:
            logger.warning(f"发送 OneBot 新好友欢迎失败 user={user_id}: {exc}")
            return False

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_notice(self, event: AstrMessageEvent):
        """监听所有事件，只处理入群和新好友事件。"""
        raw = self._raw_event(event)
        if not raw:
            return

        post_type = str(self._get(raw, "post_type", "")).lower()
        notice_type = str(self._get(raw, "notice_type", "")).lower()
        request_type = str(self._get(raw, "request_type", "")).lower()

        # OneBot v11: notice/group_increase；部分实现可能省略 post_type。
        is_group_increase = notice_type in {"group_increase", "group_increase_notice"}
        if is_group_increase:
            group_id = str(self._get(raw, "group_id", "")).strip()
            user_id = str(self._get(raw, "user_id", "")).strip()
            if not group_id or not user_id:
                return
            allowed_groups = self._allowed_groups()
            # 只要配置了群号，就只对配置中的群生效；空列表代表不启用群迎新。
            if not allowed_groups or group_id not in allowed_groups:
                return
            if not self._is_onebot_event(event, raw):
                return
            text = self._welcome_text()
            if not text:
                return
            sent = await self._send_onebot_group_welcome(event, group_id, user_id, text)
            if sent:
                logger.info(f"已发送入群欢迎 group={group_id} user={user_id}")
            return

        # OneBot v11: notice/friend_add 是已加好友通知；request/friend 作为兼容兜底。
        is_friend_added = notice_type in {"friend_add", "friend_added"}
        is_friend_request = post_type == "request" and request_type == "friend"
        if not (is_friend_added or is_friend_request):
            return

        text = self._friend_text()
        if not text:
            return

        user_id = str(self._get(raw, "user_id", "")).strip()
        if not user_id:
            try:
                user_id = str(event.get_sender_id() or "").strip()
            except Exception:
                user_id = ""

        # 某些实现会连续发 request/friend 和 notice/friend_add，短时间内只欢迎一次。
        now = time.monotonic()
        if user_id and now - self._friend_greeted_at.get(user_id, 0.0) < 30:
            return
        if user_id:
            self._friend_greeted_at[user_id] = now

        if self._is_onebot_event(event, raw) and user_id:
            if await self._send_onebot_private_welcome(event, user_id, text):
                logger.info(f"已发送新好友欢迎 user={user_id}")
                return

        # 让 AstrBot 按当前平台的私聊会话发送，兼容非 OneBot 适配器。
        try:
            yield event.plain_result(text)
            logger.info("已发送新好友欢迎消息")
        except Exception as exc:
            logger.warning(f"发送新好友欢迎失败: {exc}")


__all__ = ["GroupWelcomePlugin"]


