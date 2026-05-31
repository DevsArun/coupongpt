"""Background scheduler worker.

Runs periodic maintenance independently of the API tier using only the stdlib
asyncio loop (no extra dependency). Each task has its own interval (configurable
via env; ``0`` disables it):

  * ingest          — run due ingestion sources
  * expire           — mark past-expiry coupons as expired
  * payment_retry    — bump due failed-payment retries

Run it as a separate process/container:

    python -m app.worker
"""
from __future__ import annotations

import asyncio
import contextlib

from app.core.config import settings
from app.core.database import SessionFactory, dispose_engine
from app.core.logging import configure_logging, get_logger
from app.core.redis import close_redis

logger = get_logger("worker")


async def _run_ingest() -> None:
    from app.ingestion.pipeline import run_due_sources

    async with SessionFactory() as db:
        job_ids = await run_due_sources(db, limit=20)
        await db.commit()
        logger.info("scheduler_ingest", jobs=len(job_ids))


async def _run_expire() -> None:
    from app.services.coupon_service import expire_stale

    async with SessionFactory() as db:
        n = await expire_stale(db)
        await db.commit()
        if n:
            logger.info("scheduler_expire", expired=n)


async def _run_payment_retry() -> None:
    from app.services.billing_service import retry_failed_payments

    async with SessionFactory() as db:
        n = await retry_failed_payments(db)
        await db.commit()
        if n:
            logger.info("scheduler_payment_retry", retried=n)


async def _loop(name: str, interval: int, fn) -> None:
    """Run ``fn`` every ``interval`` seconds; never let one failure kill the loop."""
    if interval <= 0:
        logger.info("scheduler_task_disabled", task=name)
        return
    # Stagger first run slightly so tasks don't all fire at boot.
    await asyncio.sleep(min(interval, 15))
    while True:
        try:
            await fn()
        except Exception as exc:  # noqa: BLE001
            logger.error("scheduler_task_failed", task=name, error=str(exc))
        await asyncio.sleep(interval)


async def main() -> None:
    configure_logging()
    logger.info(
        "worker_start",
        ingest=settings.ingest_interval_seconds,
        expire=settings.expire_interval_seconds,
        payment_retry=settings.payment_retry_interval_seconds,
    )
    tasks = [
        asyncio.create_task(_loop("ingest", settings.ingest_interval_seconds, _run_ingest)),
        asyncio.create_task(_loop("expire", settings.expire_interval_seconds, _run_expire)),
        asyncio.create_task(
            _loop("payment_retry", settings.payment_retry_interval_seconds, _run_payment_retry)
        ),
    ]
    try:
        await asyncio.gather(*tasks)
    finally:
        await close_redis()
        await dispose_engine()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
