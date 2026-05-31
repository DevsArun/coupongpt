"""SQLAlchemy ORM models.

Importing this package registers every model with the declarative ``Base`` so
that relationship string references resolve and metadata is complete.
"""
from app.core.database import Base
from app.models.billing import (
    Invoice,
    Payment,
    PaymentMethod,
    Plan,
    Subscription,
    WebhookEvent,
)
from app.models.catalog import Category, Merchant, MerchantAlias
from app.models.coupon import (
    Coupon,
    CouponCategory,
    CouponFeedback,
    CouponValidationEvent,
)
from app.models.engagement import (
    DealAlert,
    Notification,
    Referral,
    SavedCoupon,
    Watchlist,
)
from app.models.ingestion import CrawlJob, Source
from app.models.rbac import Permission, Role, role_permissions
from app.models.search import SearchQuery, Synonym
from app.models.system import AIProvider, AIUsageLog, FeatureFlag, QueueJob, Setting
from app.models.user import AuditLog, PasswordReset, RefreshToken, User

__all__ = [
    "Base",
    "Role",
    "Permission",
    "role_permissions",
    "User",
    "RefreshToken",
    "PasswordReset",
    "AuditLog",
    "Merchant",
    "MerchantAlias",
    "Category",
    "Source",
    "CrawlJob",
    "Coupon",
    "CouponCategory",
    "CouponValidationEvent",
    "CouponFeedback",
    "SavedCoupon",
    "Watchlist",
    "DealAlert",
    "Notification",
    "Referral",
    "SearchQuery",
    "Synonym",
    "Plan",
    "Subscription",
    "PaymentMethod",
    "Payment",
    "Invoice",
    "WebhookEvent",
    "AIProvider",
    "AIUsageLog",
    "FeatureFlag",
    "Setting",
    "QueueJob",
]
