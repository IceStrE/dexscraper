# 🚦 Новая рабочая инструкция запуска DexScraper

Эти шаги обходят устаревшие подсказки и описывают реальное рабочее поведение CLI и Python‑API в текущем репозитории.

## 1. Требования
- Python 3.9+ с `pip`.
- Сетевой доступ к `wss://io.dexscreener.com`. При желании можно включить Cloudflare bypass.
- Дополнительно: `rich` для графического терминала.

## 2. Подготовка окружения
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .          # базовые зависимости (websockets + cloudscraper)
pip install -e .[dev]     # все dev-инструменты (pytest, black, mypy и т.д.)
pip install rich          # нужно только для режима --format rich
```

Альтернатива без активации venv: `python3 -m pip install -e .`.

## 3. Быстрый старт CLI
CLI публикуется как консольная команда `dexscraper` (entrypoint `dexscraper.cli:cli_main`). По умолчанию она стримит трендовые пары Solana (24h, сортировка по тренд‑скор):
```bash
dexscraper                   # бесконечный стрим, вывод JSON на stdout каждые ~5 секунд
dexscraper --once            # однократный снимок и выход
dexscraper --debug           # подробные логи
```

Полезные переключатели подключения:
```bash
--rate-limit 4.0             # запросов/сек (по умолчанию 4.0)
--max-retries 5              # попыток переподключения
--cloudflare-bypass          # включает CloudflareBypass
```

## 4. Предустановленные режимы (флаг --mode)
Каждый режим принимает `--chain` или `--chains` и строит готовую конфигурацию:
```bash
dexscraper --mode trending --chain solana           # трендовые пары
dexscraper --mode top --chain ethereum --min-liquidity 25000 --min-txns 50
dexscraper --mode gainers --chain base              # топ по росту цены
dexscraper --mode new --chain solana --max-age 6    # новые пары (часы)
dexscraper --mode transactions --chain bsc          # сортировка по транзакциям
dexscraper --mode boosted --chain polygon --min-boosts 1
```
Если `--mode` не указан, конфигурация собирается вручную из фильтров.

## 5. Кастомные фильтры
Основные параметры (все можно комбинировать):
- Цепочки: `--chain solana` или `--chains solana,ethereum`.
- Таймфрейм: `--timeframe m5|h1|h6|h24`.
- DEX: `--dex raydium` или `--dexs raydium,uniswapv3`.
- Ранжирование: `--rank-by trendingScoreH6|volume|txns|priceChangeH24|priceChangeH6|priceChangeH1|liquidity|fdv|marketCap` плюс `--order asc|desc`.
- Ликвидность/объём/транзакции: `--min-liquidity`, `--min-volume`, `--min-volume-h6`, `--min-volume-h1`, `--min-txns`, `--min-txns-h6`, `--min-txns-h1` и соответствующие `--max-*`.
- Возраст пары: `--min-age`, `--max-age` (часы).
- Изменение цены: `--min-change`, `--max-change`, `--min-change-h6`, `--min-change-h1` и `--max-*` аналоги.
- Оценки: `--min-fdv`, `--min-mcap`, `--max-fdv`, `--max-mcap`.
- Дополнительно: `--enhanced` (только пары с расширенным профилем), `--min-boosts`, `--min-ads`.

## 6. Форматы вывода
- `--format json` (дефолт): структурированный JSON `enhanced_tokens`.
- `--format ohlcv` или `ohlcvt`: CSV‑строки OHLCV/с таймстемпом и тикером.
- `--format ohlc`: CSV по каждой паре (base symbol, timestamp, o/h/l/c/vol).
- `--format mt5`: строки MetaTrader 5.
- `--format rich`: тёмный Rich UI (нужен пакет `rich`).

## 7. Rich UI и меню
```bash
pip install rich
DEXSCRAPER_THEME=dark dexscraper --format rich   # запускает SlickCLI меню
```
Выберите в меню стрим/экспорт/мониторинг. Завершение — пункт `Exit` или Ctrl+C.

## 8. Программное использование
```python
import asyncio
from dexscraper import DexScraper
from dexscraper.config import Chain, RankBy, ScrapingConfig

config = ScrapingConfig(
    chains=[Chain.SOLANA, Chain.ETHEREUM],
    rank_by=RankBy.VOLUME,
)

async def main():
    scraper = DexScraper(debug=True, config=config)
    batch = await scraper.extract_token_data()
    for token in batch.get_top_tokens(5):
        print(token.to_dict())

asyncio.run(main())
```

### Потоковый режим вручную
```python
import asyncio
from dexscraper import DexScraper

async def stream():
    scraper = DexScraper()
    while True:
        batch = await scraper.extract_token_data()
        print(batch.to_csv_string("ohlcvt"))
        await asyncio.sleep(5)

asyncio.run(stream())
```

## 9. Совместимость со старым скриптом
Команда `python dex.py` остаётся: она включает `debug=True` и стримит топ‑10 токенов в JSON каждые ~5 секунд. Остановка — Ctrl+C.

## 10. Makefile ярлыки
Для локальной разработки можно использовать готовые цели:
```bash
make install          # pip install -e .
make install-dev      # +dev-инструменты
make run              # python -m dexscraper (тот же CLI)
make stream           # asyncio.run(main()) — стрим в текущем терминале
make demo             # разовый прогон + вывод топ-5
make export-csv       # выгрузка в tokens.csv (формат ohlcvt)
make export-mt5       # выгрузка в MT5 формат
make test             # pytest -v
make docker-build && make docker-run   # собрать/запустить контейнер
```

## 11. Минимальный контроль работы
- Убедитесь, что выходные данные появляются каждые ~5 секунд (параметр `--once` отключает цикл).
- При ошибках сети перезапуск выполняется с экспоненциальной задержкой до `--max-retries` попыток.
- Логи (`--debug`) пишутся через `logging.basicConfig` в stdout/stderr.

## 12. Шаблон проверки проблем
Если возникли ошибки, соберите логи с `--debug` или из `dex.py`. Минимально сохраните:
- команду запуска с параметрами;
- вывод stdout/stderr за последние 50–100 строк;
- наличие/отсутствие пакета `rich`, если UI не стартует.
