"""Cienka warstwa obslugi wiadomosci Discord i delegacji do AI."""

from __future__ import annotations

import inspect
import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

import discord

try:
    from bot.config_manager import config_manager
except ImportError:
    try:
        from config_manager import config_manager  # type: ignore
    except Exception:
        config_manager = None

try:
    from api.api_menager import APIManager, APIManagerError, APIManagerHTTPError
except Exception:
    APIManager = None  # type: ignore

    class APIManagerError(Exception):
        pass

    class APIManagerHTTPError(APIManagerError):
        status_code: int = 0

from libs.shared.schemas.challenge import ChallengeRead

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AIProcessingRequest:
    """Ustandaryzowany payload przekazywany z bota do modulu AI."""

    message_id: str
    author_id: str
    author_display_name: str
    channel_id: str
    content: str
    image_urls: list[str] = field(default_factory=list)
    created_at: Optional[str] = None


@dataclass(slots=True)
class AIProcessingResult:
    """Wynik przetwarzania zwracany przez modul AI do bota."""

    status: str
    reaction: Optional[str] = None
    reply_text: Optional[str] = None
    reply_embed: Optional[dict[str, Any]] = None


class AIMessageProcessor(Protocol):
    """Kontrakt dla modulu AI obslugujacego wiadomosci Discord."""

    async def process_message(self, request: AIProcessingRequest) -> AIProcessingResult:
        ...


class ModuleAIMessageProcessor:
    """Adapter pod przyszly punkt wejscia z pakietu ai.services."""

    def __init__(self) -> None:
        self._process_message = None
        self._resolve_processor()

    def _resolve_processor(self) -> None:
        try:
            from ai import services as ai_services
        except Exception:
            logger.warning("Could not import ai.services", exc_info=True)
            return

        self._process_message = getattr(ai_services, "invoke_message_analysis", None)
        if self._process_message is None:
            self._process_message = getattr(ai_services, "process_discord_message", None)

    async def process_message(self, request: AIProcessingRequest) -> AIProcessingResult:
        if self._process_message is None:
            # Retry resolution in runtime in case startup import failed once.
            self._resolve_processor()

        if self._process_message is None:
            logger.warning(
                "AI message processor is not configured",
                extra={
                    "message_id": request.message_id,
                    "ai_entrypoint": "ai.services.invoke_message_analysis|ai.services.process_discord_message",
                },
            )
            return AIProcessingResult(status="ignored")

        result = self._process_message(request)
        if inspect.isawaitable(result):
            result = await result

        if isinstance(result, AIProcessingResult):
            return result

        if isinstance(result, dict):
            return AIProcessingResult(
                status=str(result.get("status", "ignored")),
                reaction=result.get("reaction"),
                reply_text=result.get("reply_text"),
                reply_embed=result.get("reply_embed"),
            )

        raise TypeError("AI processor must return AIProcessingResult or dict")


class DiscordMessageHandler:
    """Transportowa obsluga eventu Discord bez logiki biznesowej."""

    def __init__(
        self,
        ai_processor: AIMessageProcessor,
        api_manager: Optional[Any] = None,
        bot: Optional[Any] = None,
    ) -> None:
        self._ai_processor = ai_processor
        self._activity_keywords = self._load_activity_keywords()
        self._api_manager = api_manager or self._build_api_manager()
        self._bot = bot

    async def handle(self, message: discord.Message, quiet_mode: bool = False) -> None:
        should_analyze, has_keywords, has_image = self._should_forward_to_ai(message)
        if not should_analyze:
            return

        # Skip duplicate activity messages before any AI call.
        if (has_keywords or has_image) and self._activity_already_exists(message):
            logger.info(
                "Skipping duplicate message",
                extra={"message_id": message.id, "author": str(message.author)},
            )
            if (not quiet_mode) and (not any(str(r.emoji) == "✅" for r in message.reactions)):
                await message.add_reaction("✅")
            return

        request = self._build_request(message)

        if not quiet_mode:
            await message.add_reaction("🤔")

        try:
            result = await self._ai_processor.process_message(request)
        except Exception:
            if not quiet_mode:
                await self._safe_remove_reaction(message, "🤔")
            logger.error(
                "AI message processing failed",
                exc_info=True,
                extra={"message_id": message.id, "channel_id": message.channel.id},
            )
            if not quiet_mode:
                await message.add_reaction("❓")
            return

        if quiet_mode:
            return

        await self._safe_remove_reaction(message, "🤔")
        await self._apply_result(message, result)

    @staticmethod
    async def _safe_remove_reaction(message: discord.Message, emoji: str) -> None:
        try:
            await message.remove_reaction(emoji, message.guild.me if message.guild else message.author)
        except Exception:
            return

    @staticmethod
    def _normalize_datetime_for_discord(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    async def sync_active_challenges(self, challenges: list[ChallengeRead]) -> dict[str, int]:
        """Synchronizuje backlog wszystkich aktywnych challenge'y przy starcie bota."""
        summary = {
            "challenge_count": len(challenges),
            "scanned": 0,
            "queued": 0,
            "duplicates": 0,
            "processed": 0,
            "failed": 0,
            "skipped": 0,
        }

        if self._api_manager is None:
            logger.warning("Startup sync skipped: api_manager not available")
            return summary

        if self._bot is None:
            logger.warning("Startup sync skipped: bot reference not available")
            return summary

        if not challenges:
            logger.info("Startup sync skipped: no active challenges")
            return summary

        logger.info("Starting startup sync for active challenges", extra={"challenge_count": len(challenges)})

        for challenge in challenges:
            channel_id = challenge.discord_channel_id
            if not channel_id:
                summary["skipped"] += 1
                continue

            try:
                channel = self._bot.get_channel(int(channel_id))
                if channel is None:
                    channel = await self._bot.fetch_channel(int(channel_id))
            except Exception:
                summary["failed"] += 1
                logger.error(
                    "Failed to fetch challenge channel",
                    exc_info=True,
                    extra={"challenge_id": challenge.id, "channel_id": channel_id},
                )
                continue

            start_at = self._normalize_datetime_for_discord(challenge.start_date) - timedelta(seconds=1)
            end_at = self._normalize_datetime_for_discord(challenge.end_date) + timedelta(seconds=1)

            async for message in channel.history(limit=None, after=start_at, before=end_at, oldest_first=True):
                summary["scanned"] += 1
                should_analyze, _, _ = self._should_forward_to_ai(message)
                if not should_analyze:
                    continue

                summary["queued"] += 1

                if self._activity_already_exists(message):
                    summary["duplicates"] += 1
                    continue

                try:
                    await self.handle(message, quiet_mode=True)
                    summary["processed"] += 1
                except Exception:
                    summary["failed"] += 1
                    logger.error(
                        "Failed to process startup sync message",
                        exc_info=True,
                        extra={"challenge_id": challenge.id, "message_id": message.id},
                    )

        logger.info("Startup sync completed", extra=summary)
        return summary

    def _should_forward_to_ai(self, message: discord.Message) -> tuple[bool, bool, bool]:
        if message.author.bot:
            return False, False, False

        if message.content.startswith("!"):
            return False, False, False

        if getattr(message.type, "value", None) == 19:
            return False, False, False

        has_activity_keywords = bool(
            self._detect_activity_type_from_text(message.content) if message.content else None
        )
        has_image = bool(self._extract_image_urls(message))
        return (has_activity_keywords or has_image), has_activity_keywords, has_image

    def _load_activity_keywords(self) -> dict[str, list[str]]:
        if config_manager is None:
            return {}
        try:
            return config_manager.get_activity_keywords()
        except Exception:
            logger.warning("Could not load activity keywords", exc_info=True)
            return {}

    def _build_api_manager(self) -> Optional[Any]:
        if APIManager is None:
            return None
        try:
            return APIManager()
        except Exception:
            logger.warning("Could not initialize APIManager for duplicate checks", exc_info=True)
            return None

    def _detect_activity_type_from_text(self, text: str) -> Optional[str]:
        if not text or len(text) < 3 or not self._activity_keywords:
            return None

        text_lower = text.lower()
        for activity_type, keywords in self._activity_keywords.items():
            if any(str(keyword).lower() in text_lower for keyword in keywords):
                return activity_type
        return None

    def _create_unique_id(self, message: discord.Message) -> str:
        timestamp_int = int(message.created_at.timestamp())
        return f"{timestamp_int}_{message.id}"

    def _activity_already_exists(self, message: discord.Message) -> bool:
        if self._api_manager is None:
            return False

        iid = self._create_unique_id(message)
        try:
            self._api_manager.get_activity(iid)
            return True
        except APIManagerHTTPError as exc:
            if getattr(exc, "status_code", None) == 404:
                return False
            logger.warning("API error checking duplicate", exc_info=True, extra={"iid": iid})
            return False
        except APIManagerError:
            logger.warning("Connection error checking duplicate", exc_info=True, extra={"iid": iid})
            return False
        except Exception:
            logger.warning("Unexpected error checking duplicate", exc_info=True, extra={"iid": iid})
            return False

    def _build_request(self, message: discord.Message) -> AIProcessingRequest:
        return AIProcessingRequest(
            message_id=str(message.id),
            author_id=str(message.author.id),
            author_display_name=message.author.display_name,
            channel_id=str(message.channel.id),
            content=message.content or "",
            image_urls=self._extract_image_urls(message),
            created_at=message.created_at.isoformat() if message.created_at else None,
        )

    @staticmethod
    def _extract_image_urls(message: discord.Message) -> list[str]:
        image_urls: list[str] = []
        for attachment in message.attachments:
            if (
                attachment.content_type
                and attachment.content_type.startswith("image/")
                and attachment.content_type != "image/gif"
            ):
                image_urls.append(attachment.url)
        return image_urls

    async def _apply_result(self, message: discord.Message, result: AIProcessingResult) -> None:
        if result.reaction:
            await message.add_reaction(result.reaction)

        if result.reply_embed:
            await message.reply(embed=discord.Embed.from_dict(result.reply_embed))
            return

        if result.reply_text:
            await message.reply(result.reply_text)
