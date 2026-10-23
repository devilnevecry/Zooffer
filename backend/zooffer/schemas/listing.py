from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from zooffer.core.enums import AnimalSize, ListingPurpose, Sex, Species
from zooffer.core.utils import normalize_whitespace
from zooffer.schemas.public import PublicListingCardView, PublicListingView


class AnimalCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    species: Species
    breed_id: int | None = None
    breed_text: str | None = Field(default=None, max_length=120)
    sex: Sex = Sex.UNKNOWN
    birth_date: date | None = None
    colour: str | None = Field(default=None, max_length=80)
    size: AnimalSize = AnimalSize.UNKNOWN
    has_pedigree: bool = False
    pedigree_registry: str | None = Field(default=None, max_length=40)
    pedigree_number: str | None = Field(default=None, max_length=80)
    vaccinated: bool | None = None
    health_notes: str | None = Field(default=None, max_length=2000)
    description: str | None = Field(default=None, max_length=4000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = normalize_whitespace(value)
        if not cleaned:
            raise ValueError("Укажите имя животного")
        return cleaned

    @model_validator(mode="after")
    def pedigree_consistency(self) -> AnimalCreateRequest:
        if self.has_pedigree and not self.pedigree_registry:
            raise ValueError("Укажите реестр родословной (например, РКФ, FCI, WCF)")
        if not self.has_pedigree:
            self.pedigree_registry = None
            self.pedigree_number = None
        if self.birth_date and self.birth_date > date.today():
            raise ValueError("Дата рождения не может быть в будущем")
        return self


class AnimalUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=80)
    breed_id: int | None = None
    breed_text: str | None = Field(default=None, max_length=120)
    sex: Sex | None = None
    birth_date: date | None = None
    colour: str | None = Field(default=None, max_length=80)
    size: AnimalSize | None = None
    has_pedigree: bool | None = None
    pedigree_registry: str | None = Field(default=None, max_length=40)
    pedigree_number: str | None = Field(default=None, max_length=80)
    vaccinated: bool | None = None
    health_notes: str | None = Field(default=None, max_length=2000)
    description: str | None = Field(default=None, max_length=4000)


class AnimalOwnerView(BaseModel):
    public_id: UUID
    name: str
    species: Species
    breed: str | None
    sex: str
    birth_date: date | None
    colour: str | None
    size: str
    has_pedigree: bool
    pedigree_registry: str | None
    pedigree_number: str | None
    vaccinated: bool | None
    health_notes: str | None
    description: str | None
    archived_at: datetime | None
    photos: list[dict[str, object]] = Field(default_factory=list)


class ListingCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    animal_id: UUID
    purpose: ListingPurpose
    title: str = Field(min_length=5, max_length=140)
    description: str = Field(default="", max_length=5000)
    price_kopecks: int | None = Field(default=None, ge=0, le=100_000_000)
    negotiable: bool = False
    city_id: int | None = None
    region_id: int | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        return normalize_whitespace(value)

    @model_validator(mode="after")
    def price_rules(self) -> ListingCreateRequest:
        if self.purpose == ListingPurpose.ADOPTION and self.price_kopecks:
            raise ValueError("Для объявления «Отдам в добрые руки» цена не указывается")
        if (
            self.purpose == ListingPurpose.SALE
            and self.price_kopecks is None
            and not self.negotiable
        ):
            raise ValueError("Укажите цену или отметьте «По договорённости»")
        return self


class ListingUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=5, max_length=140)
    description: str | None = Field(default=None, max_length=5000)
    price_kopecks: int | None = Field(default=None, ge=0, le=100_000_000)
    negotiable: bool | None = None
    city_id: int | None = None
    region_id: int | None = None


class PublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm_adult: bool
    confirm_animal_welfare: bool
    confirm_photo_rights: bool
    confirm_no_prohibited: bool
    confirm_accuracy: bool

    @model_validator(mode="after")
    def all_confirmed(self) -> PublishRequest:
        if not all(
            [
                self.confirm_adult,
                self.confirm_animal_welfare,
                self.confirm_photo_rights,
                self.confirm_no_prohibited,
                self.confirm_accuracy,
            ]
        ):
            raise ValueError("Для публикации подтвердите все обязательные пункты")
        return self


class ListingOwnerView(BaseModel):
    public_id: UUID
    slug: str
    title: str
    description: str
    purpose: ListingPurpose
    status: str
    price_kopecks: int | None
    currency: str
    negotiable: bool
    city_id: int | None
    region_id: int | None
    animal_id: UUID
    animal_public_id: UUID
    published_at: datetime | None
    expires_at: datetime | None
    moderation_reason: str | None
    created_at: datetime
    updated_at: datetime


class ListingDetailResponse(BaseModel):
    listing: PublicListingView


class ListingCardPageResponse(BaseModel):
    items: list[PublicListingCardView]
    next_cursor: str | None
    has_more: bool


class AnimalPhotoOwnerView(BaseModel):
    id: UUID
    url: str
    thumb_url: str
    width: int
    height: int
    position: int
    is_primary: bool
    alt_text: str | None = None


class AnimalDocumentOwnerView(BaseModel):
    id: UUID
    document_type: str
    status: str
    content_type: str
    created_at: datetime


class DictionaryItem(BaseModel):
    id: int
    name: str
    slug: str | None = None
    region_id: int | None = None
    species: str | None = None


class DictionariesResponse(BaseModel):
    regions: list[DictionaryItem]
    cities: list[DictionaryItem]
    breeds: list[DictionaryItem]
