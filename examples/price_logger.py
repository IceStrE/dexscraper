"""
Тестовый скрипт для запуска WebSocket DexScreener и логирования цены по заданному токену.

Использует встроенный `DexScraper` и фильтрует данные по адресу или символу токена.
"""

import asyncio
import logging
from datetime import datetime
from typing import Iterable, Optional

from dexscraper import DexScraper
from dexscraper.config import PresetConfigs
from dexscraper.models import ExtractedTokenBatch, TokenProfile, TradingPair

TARGET_TOKEN = "2TRAviWGVy7V1y8mGbLanrEawZoK7JxQTEAjE5xRpump"


class MillisecondFormatter(logging.Formatter):
    """Форматер, который выводит время в виде [HH:MM:SS.mmm]."""

    converter = datetime.fromtimestamp

    def formatTime(self, record, datefmt=None):  # noqa: D401
        timestamp = self.converter(record.created)
        return timestamp.strftime("%H:%M:%S.%f")[:-3]


def configure_logger() -> logging.Logger:
    """Создаёт консольный логгер с миллисекундной меткой времени."""

    logger = logging.getLogger("price_logger")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(
        MillisecondFormatter(fmt="[%(asctime)s] %(levelname)s %(message)s")
    )

    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def find_target(tokens: Iterable[TokenProfile]) -> Optional[TokenProfile]:
    """Возвращает профиль токена, совпадающий по адресу или символу."""

    lowered_target = TARGET_TOKEN.lower()
    for token in tokens:
        candidates = filter(None, [token.pair_address, token.token_address, token.symbol])
        for candidate in candidates:
            if candidate.lower() == lowered_target:
                return token
    return None


def log_batch(batch: ExtractedTokenBatch, logger: logging.Logger) -> None:
    """Печатает цену целевого токена из полученного батча."""

    target = find_target(batch.tokens)
    if not target:
        logger.info("Токен не найден в текущем батче")
        return

    if target.price is None:
        logger.info("Цена не указана, попробуйте позже")
        return

    change = (
        f", 24ч: {target.change_24h:+.2f}%" if target.change_24h is not None else ""
    )
    logger.info(
        "Цена %s: %.8f USD%s (пара: %s, символ: %s)",
        TARGET_TOKEN,
        target.price,
        change,
        target.pair_address or "—",
        target.symbol or "—",
    )


def log_legacy_pairs(pairs: Iterable[TradingPair], logger: logging.Logger) -> None:
    """Поддержка старого формата, если он передан в колбэк."""

    for pair in pairs:
        if pair.pair_address.lower() == TARGET_TOKEN.lower():
            logger.info(
                "Цена %s: %.8f USD (DEX %s)",
                TARGET_TOKEN,
                pair.price_data.usd if pair.price_data else 0.0,
                pair.protocol,
            )
            return
    logger.info("Токен не найден в текущем списке пар")


async def main() -> None:
    logger = configure_logger()

    scraper = DexScraper(
        debug=False,
        use_cloudflare_bypass=False,
        config=PresetConfigs.pumpfun_trending(),
    )

    def handle_stream(data):
        if isinstance(data, ExtractedTokenBatch):
            log_batch(data, logger)
        else:
            log_legacy_pairs(data, logger)

    await scraper.stream_pairs(callback=handle_stream, use_enhanced_extraction=True)


if __name__ == "__main__":
    asyncio.run(main())
