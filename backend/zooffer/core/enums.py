from __future__ import annotations

from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class UserRole(StrEnum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class AuthProvider(StrEnum):
    # Provider identifier stored in the database; not a credential.
    PASSWORD = "password"  # nosec B105
    TELEGRAM = "telegram"


class ListingPurpose(StrEnum):
    SALE = "sale"
    MATING = "mating"
    BREEDING_PEDIGREE = "breeding_pedigree"
    ADOPTION = "adoption"
    REHOMING = "rehoming"


class ListingStatus(StrEnum):
    DRAFT = "draft"
    PENDING_MODERATION = "pending_moderation"
    PUBLISHED = "published"
    PAUSED = "paused"
    EXPIRED = "expired"
    SOLD = "sold"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class Species(StrEnum):
    DOG = "dog"
    CAT = "cat"
    BIRD = "bird"
    RODENT = "rodent"
    REPTILE = "reptile"
    OTHER = "other"


class Sex(StrEnum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class AnimalSize(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    UNKNOWN = "unknown"


class SwipeAction(StrEnum):
    LIKE = "like"
    SKIP = "skip"


class SwipeSource(StrEnum):
    WEB = "web"
    BOT = "bot"
    MINIAPP = "miniapp"


class ConversationType(StrEnum):
    MATCH = "match"
    INQUIRY = "inquiry"


class SubscriptionStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"


class OrderStatus(StrEnum):
    CREATED = "created"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class PartnerStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class OfferCategory(StrEnum):
    FOOD = "food"
    STORES = "stores"
    VET = "vet"
    GROOMING = "grooming"
    SERVICES = "services"


class ReportStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ModerationDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"
    SHADOW_LIMIT = "shadow_limit"
    SUSPEND = "suspend"
    BAN = "ban"


class NotificationChannel(StrEnum):
    IN_APP = "in_app"
    TELEGRAM = "telegram"
    EMAIL = "email"


class Entitlement(StrEnum):
    UNLIMITED_SWIPES = "unlimited_swipes"
    UNDO = "undo"
    SEE_WHO_LIKED = "see_who_liked"
    BOOST = "boost"
    EXTENDED_PHOTOS = "extended_photos"
    PRIORITY_MODERATION = "priority_moderation"
    AD_FREE = "ad_free"
