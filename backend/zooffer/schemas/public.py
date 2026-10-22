from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zooffer.core.enums import ListingPurpose, Species


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PublicOwnerView(BaseModel):
    """The ONLY owner identity exposed to other users. Never add contact/account fields."""

    display_name: str | None = None


class PublicPhotoView(BaseModel):
    url: str
    alt: str | None = None
    width: int
    height: int
    is_primary: bool = False


class PublicAnimalView(BaseModel):
    public_id: UUID
    name: str
    species: Species
    breed: str | None = None
    sex: str
    age_years: int | None = None
    birth_date: date | None = None
    colour: str | None = None
    size: str
    has_pedigree: bool
    pedigree_registry: str | None = None
    vaccinated: bool | None = None
    health_notes: str | None = None
    description: str | None = None
    photos: list[PublicPhotoView] = Field(default_factory=list)
    has_pedigree_document: bool = False


class PublicCityView(BaseModel):
    name: str
    slug: str


class PublicRegionView(BaseModel):
    name: str
    slug: str


class PublicListingCardView(BaseModel):
    public_id: UUID
    slug: str
    title: str
    purpose: ListingPurpose
    price_kopecks: int | None = None
    currency: str = "RUB"
    negotiable: bool = False
    city: PublicCityView | None = None
    primary_photo: PublicPhotoView | None = None
    animal_name: str
    species: Species
    breed: str | None = None
    sex: str
    age_years: int | None = None
    has_pedigree: bool
    has_pedigree_document: bool = False
    is_featured: bool = False
    published_at: datetime | None = None
    owner: PublicOwnerView


class PublicListingView(BaseModel):
    public_id: UUID
    slug: str
    title: str
    description: str
    purpose: ListingPurpose
    price_kopecks: int | None = None
    currency: str = "RUB"
    negotiable: bool = False
    city: PublicCityView | None = None
    region: PublicRegionView | None = None
    published_at: datetime | None = None
    expires_at: datetime | None = None
    is_featured: bool = False
    animal: PublicAnimalView
    owner: PublicOwnerView


class PublicPartnerOfferView(BaseModel):
    public_id: UUID
    title: str
    description: str
    category: str
    discount_code: str | None = None
    terms: str
    ends_at: datetime | None = None
    partner_name: str
    ad_label: str | None = None
    erid: str | None = None


class PageMeta(BaseModel):
    next_cursor: str | None = None
    has_more: bool = False
    total: int | None = None


class ListingPage(BaseModel):
    items: list[PublicListingCardView]
    meta: PageMeta
