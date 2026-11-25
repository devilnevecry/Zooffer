"""Import all models so Alembic and metadata creation see them."""

from zooffer.db.models.animal import Animal, AnimalDocument, AnimalPhoto
from zooffer.db.models.billing import (
    EntitlementGrant,
    PaymentEvent,
    PaymentOrder,
    Plan,
    Refund,
    Subscription,
)
from zooffer.db.models.channel import Channel, ChannelPost, ChannelSubscription
from zooffer.db.models.co_owner import AnimalCoOwner
from zooffer.db.models.discovery import Favorite, Match, Swipe
from zooffer.db.models.event import Event, EventAttendee
from zooffer.db.models.geo import Breed, City, Region
from zooffer.db.models.listing import Listing
from zooffer.db.models.lost import LostReport, LostSighting
from zooffer.db.models.market import (
    CartItem,
    Order,
    OrderItem,
    Product,
    ProductCategory,
    Shop,
)
from zooffer.db.models.messaging import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageReport,
)
from zooffer.db.models.organization import Organization
from zooffer.db.models.partner import (
    Partner,
    PartnerClick,
    PartnerConversion,
    PartnerInquiry,
    PartnerOffer,
)
from zooffer.db.models.place import Place
from zooffer.db.models.qa import Answer, Question
from zooffer.db.models.quota import DailyQuotaUsage, QuotaEvent
from zooffer.db.models.service import ServiceProfile, ServiceReview
from zooffer.db.models.story import Story, StoryBookmark, StoryComment, StoryReaction
from zooffer.db.models.system import (
    AnalyticsEvent,
    CampaignAttribution,
    LegalDocument,
    ListingSlugHistory,
    ModerationAction,
    Notification,
    NotificationDelivery,
    NotificationPreference,
    PrivacyRequest,
    Referral,
    Report,
    SavedSearch,
    SupportMessage,
    SupportTicket,
    SystemSetting,
)
from zooffer.db.models.user import (
    AccountLinkToken,
    AuditLog,
    AuthIdentity,
    AuthToken,
    Block,
    BotUpdateSeen,
    Consent,
    Credential,
    MfaFactor,
    Profile,
    TelegramChat,
    User,
    UserPrivateData,
    UserSession,
)
from zooffer.db.models.video import VideoPost

__all__ = [
    "AccountLinkToken",
    "AnalyticsEvent",
    "Animal",
    "AnimalCoOwner",
    "AnimalDocument",
    "AnimalPhoto",
    "Answer",
    "AuditLog",
    "AuthIdentity",
    "AuthToken",
    "Block",
    "BotUpdateSeen",
    "Breed",
    "CampaignAttribution",
    "CartItem",
    "Channel",
    "ChannelPost",
    "ChannelSubscription",
    "City",
    "Consent",
    "Conversation",
    "ConversationParticipant",
    "Credential",
    "DailyQuotaUsage",
    "EntitlementGrant",
    "Event",
    "EventAttendee",
    "Favorite",
    "LegalDocument",
    "Listing",
    "ListingSlugHistory",
    "LostReport",
    "LostSighting",
    "Match",
    "Message",
    "MessageReport",
    "MfaFactor",
    "ModerationAction",
    "Notification",
    "NotificationDelivery",
    "NotificationPreference",
    "Order",
    "OrderItem",
    "Organization",
    "Partner",
    "PartnerClick",
    "PartnerConversion",
    "PartnerInquiry",
    "PartnerOffer",
    "PaymentEvent",
    "PaymentOrder",
    "Place",
    "Plan",
    "PrivacyRequest",
    "Product",
    "ProductCategory",
    "Profile",
    "Question",
    "QuotaEvent",
    "Referral",
    "Refund",
    "Region",
    "Report",
    "SavedSearch",
    "ServiceProfile",
    "ServiceReview",
    "Shop",
    "Story",
    "StoryBookmark",
    "StoryComment",
    "StoryReaction",
    "Subscription",
    "SupportMessage",
    "SupportTicket",
    "Swipe",
    "SystemSetting",
    "TelegramChat",
    "User",
    "UserPrivateData",
    "UserSession",
    "VideoPost",
]
