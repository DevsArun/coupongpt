"""Operational CLI: seed data, create admins, reindex, and run ingestion.

Usage::

    python -m app.cli seed                 # super admin + demo coupons
    python -m app.cli create-admin EMAIL PASSWORD
    python -m app.cli reindex              # push active coupons to Meilisearch
    python -m app.cli sync-synonyms        # push DB synonyms to Meilisearch
    python -m app.cli ingest               # run due ingestion sources
    python -m app.cli expire               # mark stale coupons expired
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.database import SessionFactory, dispose_engine
from app.core.logging import configure_logging, get_logger
from app.core.security import generate_referral_code, hash_password, new_uuid
from app.ingestion import storage
from app.ingestion.extraction import StructuredCoupon
from app.models.catalog import Merchant
from app.models.rbac import Role
from app.models.search import Synonym
from app.models.user import User

logger = get_logger("cli")


async def create_admin(email: str, password: str) -> None:
    async with SessionFactory() as db:
        role = (await db.execute(select(Role).where(Role.slug == "super_admin"))).scalar_one_or_none()
        if role is None:
            print("super_admin role missing — run migrations (001/002) first.")
            return
        existing = (await db.execute(select(User).where(User.email == email.lower()))).scalar_one_or_none()
        if existing:
            existing.role_id = role.id
            existing.password_hash = hash_password(password)
            await db.commit()
            print(f"Updated existing user {email} to super_admin.")
            return
        user = User(
            uuid=new_uuid(),
            email=email.lower(),
            password_hash=hash_password(password),
            full_name="Super Admin",
            role_id=role.id,
            status="active",
            referral_code=generate_referral_code(),
        )
        db.add(user)
        await db.commit()
        print(f"Created super admin: {email}")


_DEMO_COUPONS = {
    "amazon": [
        ("Amazon: 20% off electronics today", "ELEC20", "percentage", 20.0),
        ("Amazon Prime: Free shipping on all orders", None, "free_shipping", None),
    ],
    "nike": [
        ("Nike: $25 off orders over $100", "NIKE25", "fixed", 25.0),
        ("Nike February sale — 30% off sneakers", "FEB30", "percentage", 30.0),
    ],
    "hostinger": [
        ("Hostinger: 75% off web hosting + free domain", "HOST75", "percentage", 75.0),
    ],
    "nordvpn": [
        ("NordVPN: 68% off 2-year plan + 3 months free", "VPN68", "percentage", 68.0),
    ],
    "adidas": [
        ("Adidas: Buy one get one 50% off", "BOGO50", "bogo", None),
    ],
}


async def seed_demo() -> None:
    async with SessionFactory() as db:
        merchants = {
            m.slug: m
            for m in (await db.execute(select(Merchant))).scalars().all()
        }
        if not merchants:
            print("No merchants found — run seed migration 002 first.")
            return

        created = 0
        for slug, coupons in _DEMO_COUPONS.items():
            merchant = merchants.get(slug)
            if not merchant:
                continue
            for title, code, dtype, dvalue in coupons:
                sc = StructuredCoupon(
                    title=title,
                    code=code,
                    discount_type=dtype,
                    discount_value=dvalue,
                    expires_at=datetime.utcnow() + timedelta(days=30),
                    landing_url=f"https://{merchant.domain or 'example.com'}",
                    confidence=0.85,
                    raw_text=title,
                )
                _c, was_created = await storage.store_coupon(
                    db,
                    sc,
                    merchant_id=merchant.id,
                    merchant_known=True,
                    merchant_trust=float(merchant.trust_score),
                    source_id=None,
                    source_trust=float(merchant.trust_score),
                    index=False,  # reindex command will push everything
                )
                created += int(was_created)
        await db.commit()
        print(f"Seeded {created} demo coupons.")


async def reindex() -> None:
    from app.services.indexing_service import reindex_all

    async with SessionFactory() as db:
        count = await reindex_all(db)
        await db.commit()
        print(f"Reindexed {count} coupons into Meilisearch.")


async def sync_synonyms() -> None:
    from app.search.client import update_synonyms

    async with SessionFactory() as db:
        rows = (await db.execute(select(Synonym).where(Synonym.is_active.is_(True)))).scalars().all()
        mapping = {r.term: r.synonyms for r in rows}
        await update_synonyms(mapping)
        print(f"Synced {len(mapping)} synonym groups to Meilisearch.")


async def ingest() -> None:
    from app.ingestion.pipeline import run_due_sources
    from app.services.alerts_service import run_alert_matching

    async with SessionFactory() as db:
        job_ids = await run_due_sources(db, limit=20)
        fired = await run_alert_matching(db)
        await db.commit()
        print(f"Ran ingestion for {len(job_ids)} sources (jobs: {job_ids}); fired {fired} alert(s).")


async def expire() -> None:
    from app.services.coupon_service import expire_stale

    async with SessionFactory() as db:
        n = await expire_stale(db)
        await db.commit()
        print(f"Expired {n} stale coupons.")


async def run_alerts() -> None:
    from app.services.alerts_service import run_alert_matching

    async with SessionFactory() as db:
        n = await run_alert_matching(db)
        await db.commit()
        print(f"Fired {n} deal-alert notification(s).")


def _split_sql(sql: str) -> list[str]:
    """Split a SQL script into individual statements on ';' terminators.

    Full-line ``--`` comments are stripped *before* splitting so that semicolons
    appearing inside comment text (e.g. "uniques uq_<table>_<cols>;") don't break
    statement boundaries. Inline comments are left in place — MySQL parses them.
    """
    no_comments = "\n".join(
        ln for ln in sql.splitlines() if not ln.lstrip().startswith("--")
    )
    statements: list[str] = []
    for chunk in no_comments.split(";"):
        cleaned = chunk.strip()
        if cleaned:
            statements.append(cleaned)
    return statements


async def migrate() -> None:
    """Apply the SQL migrations in backend/migrations in filename order."""
    import os

    from app.core.database import engine

    migrations_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "migrations")
    files = sorted(f for f in os.listdir(migrations_dir) if f.endswith(".sql"))
    if not files:
        print("No migration files found.")
        return

    for fname in files:
        path = os.path.join(migrations_dir, fname)
        with open(path, encoding="utf-8") as fh:
            statements = _split_sql(fh.read())
        async with engine.begin() as conn:
            for stmt in statements:
                await conn.exec_driver_sql(stmt)
        print(f"Applied {fname} ({len(statements)} statements).")
    print("Migrations complete.")


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="CouponGPT operational CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("seed", help="Seed demo coupons")
    sub.add_parser("migrate", help="Apply SQL migrations (schema + seed)")
    sub.add_parser("reindex", help="Reindex active coupons into Meilisearch")
    sub.add_parser("sync-synonyms", help="Push DB synonyms to Meilisearch")
    sub.add_parser("ingest", help="Run due ingestion sources")
    sub.add_parser("alerts", help="Match deal alerts and create notifications")
    sub.add_parser("expire", help="Mark stale coupons expired")
    p_admin = sub.add_parser("create-admin", help="Create or promote a super admin")
    p_admin.add_argument("email")
    p_admin.add_argument("password")

    args = parser.parse_args()

    async def _run() -> None:
        try:
            if args.command == "seed":
                await seed_demo()
            elif args.command == "migrate":
                await migrate()
            elif args.command == "reindex":
                await reindex()
            elif args.command == "sync-synonyms":
                await sync_synonyms()
            elif args.command == "ingest":
                await ingest()
            elif args.command == "alerts":
                await run_alerts()
            elif args.command == "expire":
                await expire()
            elif args.command == "create-admin":
                await create_admin(args.email, args.password)
        finally:
            await dispose_engine()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
