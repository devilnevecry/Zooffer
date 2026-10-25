import { serverFetch } from "./api";
import type {
  BlockedUserList,
  Dictionaries,
  DiscoveryFeed,
  FavoriteList,
  HomeData,
  ListingDetail,
  ListingPageData,
  MatchList,
  NotificationList,
  NotificationPreferenceList,
  OwnerAnimal,
  OwnerListing,
  PartnerOfferList,
  PlanList,
  SessionList,
  SubscriptionState,
  ConversationSummary,
} from "./types";

export interface SearchParams {
  q?: string;
  purpose?: string | string[];
  species?: string;
  breed_id?: number | string;
  sex?: string;
  min_age?: number | string;
  max_age?: number | string;
  size?: string;
  colour?: string;
  city_id?: number | string;
  region_id?: number | string;
  price_min?: number | string;
  price_max?: number | string;
  has_pedigree?: string;
  vaccinated?: string;
  with_photos?: string;
  sort?: string;
  cursor?: string;
  limit?: number | string;
}

export function toQuery(params: Record<string, unknown>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item !== undefined && item !== null && item !== "") {
          query.append(key, String(item));
        }
      }
    } else {
      query.set(key, String(value));
    }
  }
  const text = query.toString();
  return text ? `?${text}` : "";
}

export function getHome(): Promise<HomeData | null> {
  return serverFetch<HomeData>("/api/v1/public/home", { allow404: true });
}

export function getDictionaries(): Promise<Dictionaries | null> {
  return serverFetch<Dictionaries>("/api/v1/public/dictionaries", { allow404: true });
}

export function searchListings(params: SearchParams): Promise<ListingPageData | null> {
  return serverFetch<ListingPageData>(
    `/api/v1/public/listings${toQuery({ ...params, limit: params.limit ?? 24 })}`,
    { allow404: true },
  );
}

export function getPublicListing(slug: string): Promise<ListingDetail | null> {
  return serverFetch<ListingDetail>(`/api/v1/public/listings/${encodeURIComponent(slug)}`, {
    allow404: true,
  });
}

export function getDiscoveryFeed(params: SearchParams = {}): Promise<DiscoveryFeed | null> {
  return serverFetch<DiscoveryFeed>(`/api/v1/discovery/feed${toQuery({ ...params, limit: 20 })}`, {
    allow401: true,
    allow404: true,
  });
}

export function getFavorites<T>(): Promise<T | null> {
  return serverFetch<T>("/api/v1/favorites", { allow401: true });
}

export function getOwnerAnimals(): Promise<{ items: OwnerAnimal[] } | null> {
  return serverFetch<{ items: OwnerAnimal[] }>("/api/v1/animals", { allow401: true });
}

export function getOwnerListings(): Promise<OwnerListing[] | null> {
  return serverFetch<OwnerListing[]>("/api/v1/listings", { allow401: true });
}

export function getOwnerListing(id: string): Promise<OwnerListing | null> {
  return serverFetch<OwnerListing>(`/api/v1/listings/${encodeURIComponent(id)}`, {
    allow401: true,
    allow404: true,
  });
}

export function getFavoriteList(): Promise<FavoriteList | null> {
  return serverFetch<FavoriteList>("/api/v1/favorites", { allow401: true });
}

export function getMatches(): Promise<MatchList | null> {
  return serverFetch<MatchList>("/api/v1/matches", { allow401: true });
}

export function getConversationList(): Promise<{ items: ConversationSummary[] } | null> {
  return serverFetch<{ items: ConversationSummary[] }>("/api/v1/conversations", {
    allow401: true,
  });
}

export function getNotificationList(): Promise<NotificationList | null> {
  return serverFetch<NotificationList>("/api/v1/notifications?limit=100", { allow401: true });
}

export function getNotificationPreferences(): Promise<NotificationPreferenceList | null> {
  return serverFetch<NotificationPreferenceList>("/api/v1/notification-preferences", {
    allow401: true,
  });
}

export function getSessions(): Promise<SessionList | null> {
  return serverFetch<SessionList>("/api/v1/auth/sessions", { allow401: true });
}

export function getSubscriptionState(): Promise<SubscriptionState | null> {
  return serverFetch<SubscriptionState>("/api/v1/billing/subscription", { allow401: true });
}

export function getPlans(): Promise<PlanList | null> {
  return serverFetch<PlanList>("/api/v1/public/plans", { allow404: true });
}

export function getPartnerOffers(): Promise<PartnerOfferList | null> {
  return serverFetch<PartnerOfferList>("/api/v1/public/partners", { allow404: true });
}

export function getBlockedUsers(): Promise<BlockedUserList | null> {
  return serverFetch<BlockedUserList>("/api/v1/blocked-users", { allow401: true });
}
