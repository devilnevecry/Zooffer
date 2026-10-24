export type Species = "dog" | "cat" | "bird" | "rodent" | "reptile" | "other";
export type Purpose = "sale" | "mating" | "breeding_pedigree" | "adoption" | "rehoming";

export interface CityView {
  name: string;
  slug: string;
}

export interface PhotoView {
  url: string;
  alt?: string | null;
  width: number;
  height: number;
  is_primary?: boolean;
}

export interface OwnerView {
  display_name: string | null;
}

export interface ListingCard {
  public_id: string;
  slug: string;
  title: string;
  purpose: Purpose;
  price_kopecks: number | null;
  currency: string;
  negotiable: boolean;
  city: CityView | null;
  primary_photo: PhotoView | null;
  animal_name: string;
  species: Species;
  breed: string | null;
  sex: string;
  age_years: number | null;
  has_pedigree: boolean;
  has_pedigree_document: boolean;
  is_featured: boolean;
  published_at: string | null;
  owner: OwnerView;
}

export interface AnimalView {
  public_id: string;
  name: string;
  species: Species;
  breed: string | null;
  sex: string;
  age_years: number | null;
  birth_date: string | null;
  colour: string | null;
  size: string;
  has_pedigree: boolean;
  pedigree_registry: string | null;
  vaccinated: boolean | null;
  health_notes: string | null;
  description: string | null;
  photos: PhotoView[];
  has_pedigree_document: boolean;
}

export interface ListingDetail {
  public_id: string;
  slug: string;
  title: string;
  description: string;
  purpose: Purpose;
  price_kopecks: number | null;
  currency: string;
  negotiable: boolean;
  city: CityView | null;
  region: CityView | null;
  published_at: string | null;
  expires_at: string | null;
  is_featured: boolean;
  animal: AnimalView;
  owner: OwnerView;
}

export interface CategoryCount {
  purpose: Purpose;
  count: number;
}

export interface HomeData {
  featured: ListingCard[];
  recent: ListingCard[];
  categories: CategoryCount[];
}

export interface ListingPageData {
  items: ListingCard[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface DictionaryItem {
  id: number;
  name: string;
  slug?: string | null;
  region_id?: number | null;
  species?: string | null;
}

export interface Dictionaries {
  regions: DictionaryItem[];
  cities: DictionaryItem[];
  breeds: DictionaryItem[];
}

export interface SelfUser {
  public_id: string;
  email: string | null;
  role: string;
  first_name: string | null;
  last_name: string | null;
  city_id: number | null;
  onboarding_completed: boolean;
  mfa_enabled: boolean;
  created_at: string;
}

export interface MeResponse {
  user: SelfUser;
  csrf_token: string;
}

export interface AuthResponse {
  user: SelfUser;
  csrf_token: string;
}

export interface QuotaView {
  limit: number;
  used: number;
  remaining: number;
  resets_at: string;
  unlimited: boolean;
}

export interface DiscoveryFeed {
  items: ListingCard[];
  next_cursor: string | null;
  has_more: boolean;
  quota: QuotaView;
  guest: boolean;
}

export interface SwipeResponse {
  action: "like" | "skip";
  remaining: number;
  limit: number;
  resets_at: string;
  unlimited: boolean;
  match_created: boolean;
  conversation_public_id: string | null;
}

export interface OwnerListing {
  public_id: string;
  slug: string;
  title: string;
  description: string;
  purpose: Purpose;
  status: string;
  price_kopecks: number | null;
  currency: string;
  negotiable: boolean;
  city_id: number | null;
  region_id: number | null;
  animal_id: string;
  animal_public_id: string;
  published_at: string | null;
  expires_at: string | null;
  moderation_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface OwnerAnimal {
  public_id: string;
  name: string;
  species: Species;
  breed: string | null;
  sex: string;
  birth_date: string | null;
  colour: string | null;
  size: string;
  has_pedigree: boolean;
  pedigree_registry: string | null;
  pedigree_number: string | null;
  vaccinated: boolean | null;
  health_notes: string | null;
  description: string | null;
  archived_at: string | null;
  photos: {
    id: string;
    url: string;
    thumb_url: string;
    width: number;
    height: number;
    position: number;
    is_primary: boolean;
    alt_text: string | null;
  }[];
}

export interface ConversationListing {
  public_id: string;
  slug: string;
  title: string;
  animal_name: string;
  primary_photo_url: string | null;
}

export interface ConversationSummary {
  public_id: string;
  conversation_type: string;
  counterpart: OwnerView;
  listing: ConversationListing | null;
  last_message: { body: string; mine: boolean; created_at: string } | null;
  unread_count: number;
  last_message_at: string | null;
  updated_at: string;
  blocked: boolean;
}

export interface Message {
  id: string;
  body: string;
  mine: boolean;
  edited_at: string | null;
  created_at: string;
}

export interface ConversationDetail {
  conversation: ConversationSummary;
  messages: Message[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface MessagePageView {
  items: Message[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface NotificationItem {
  id: string;
  category: string;
  title: string;
  body: string;
  data: Record<string, string> | null;
  read_at: string | null;
  created_at: string;
}

export interface NotificationList {
  items: NotificationItem[];
  unread_count: number;
}

export interface FavoriteItem {
  public_id: string;
  slug: string;
  title: string;
  status: string;
  purpose: Purpose;
  price_kopecks: number | null;
  animal_name: string;
  species: Species;
  primary_photo_url?: string | null;
}

export interface MatchItem {
  conversation_public_id: string | null;
  animal_name: string;
  animal_public_id: string;
  listing_slug: string | null;
  listing_title: string | null;
  species: Species;
  breed: string | null;
  sex: string;
  primary_photo_url: string | null;
  owner_display_name: string | null;
  created_at: string;
}

export interface MatchList {
  items: MatchItem[];
}

export interface NotificationPreference {
  category: string;
  in_app: boolean;
  telegram: boolean;
  email: boolean;
  quiet_from: number | null;
  quiet_to: number | null;
}

export interface NotificationPreferenceList {
  items: NotificationPreference[];
}

export interface SupportTicket {
  public_id: string;
  subject: string;
  status: string;
  created_at: string;
}

export interface PartnerOffer {
  public_id: string;
  partner_name: string;
  partner_slug: string;
  title: string;
  description: string;
  category: string;
  discount_code: string | null;
  terms: string;
  destination_url: string;
  is_featured: boolean;
  erid: string | null;
  ad_label: string | null;
}

export interface PartnerOfferList {
  items: PartnerOffer[];
}

export interface Plan {
  code: string;
  name: string;
  description: string;
  price_kopecks: number;
  currency: string;
  stars_amount: number | null;
  period_days: number;
  entitlements: string[];
  is_placeholder_price: boolean;
}

export interface PlanList {
  items: Plan[];
}

export interface SubscriptionState {
  status: string;
  plan_code: string | null;
  plan_name: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  entitlements: string[];
  quota_limit: number;
  quota_unlimited: boolean;
  payments_available: boolean;
  payments_demo: boolean;
  payment_provider: string;
}

export interface BillingOrder {
  public_id: string;
  plan_code: string;
  provider: string;
  status: string;
  amount_kopecks: number;
  currency: string;
  confirmation_url: string | null;
  demo: boolean;
  created_at: string;
  expires_at: string | null;
  paid_at: string | null;
}

export interface SessionView {
  id: string;
  device_label: string | null;
  user_agent: string | null;
  created_at: string;
  last_seen_at: string;
  is_current: boolean;
}

export interface SessionList {
  items: SessionView[];
}

export interface AnimalList {
  items: OwnerAnimal[];
}

export interface DocumentItem {
  id: string;
  document_type: string;
  status: string;
  content_type: string;
  created_at: string;
}

export interface DocumentList {
  items: DocumentItem[];
}

export interface UnreadCount {
  unread_count: number;
}

export interface FavoriteList {
  items: FavoriteItem[];
}

export interface BlockedUser {
  id: string;
  display_name: string | null;
  blocked_at: string;
}

export interface BlockedUserList {
  items: BlockedUser[];
}

export interface OkResponse {
  ok: boolean;
}

export interface AdminStats {
  users_total: number;
  users_new_week: number;
  listings_published: number;
  listings_pending: number;
  reports_open: number;
  support_open: number;
  subscriptions_active: number;
  revenue_kopecks_30d: number;
  swipes_today: number;
  matches_total: number;
}

export interface AdminRecentItem {
  created_at: string;
  action: string;
  object_type: string;
  object_id: string | null;
  actor_role: string | null;
}

export interface AdminDashboard {
  stats: AdminStats;
  recent_actions: AdminRecentItem[];
}

export interface AdminListing {
  public_id: string;
  slug: string;
  title: string;
  purpose: string;
  status: string;
  price_kopecks: number | null;
  owner_name: string | null;
  owner_public_id: string;
  animal_name: string;
  species: string;
  city_name: string | null;
  photo_url: string | null;
  moderation_reason: string | null;
  quality_score: number;
  created_at: string;
  published_at: string | null;
}

export interface AdminListingList {
  items: AdminListing[];
  total: number;
}

export interface AdminReport {
  id: string;
  target_type: string;
  target_public_id: string;
  reason: string;
  details: string | null;
  status: string;
  reporter_name: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface AdminReportList {
  items: AdminReport[];
}

export interface AdminUser {
  public_id: string;
  display_name: string | null;
  email: string | null;
  role: string;
  status: string;
  city_name: string | null;
  listings_count: number;
  created_at: string;
  mfa_enabled: boolean;
}

export interface AdminUserList {
  items: AdminUser[];
  total: number;
}

export interface AdminSupportTicket {
  public_id: string;
  subject: string;
  status: string;
  channel: string;
  user_name: string | null;
  last_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminSupportList {
  items: AdminSupportTicket[];
}

export interface AdminSetting {
  key: string;
  value: string;
  updated_at: string | null;
}

export interface AdminSettings {
  items: AdminSetting[];
}

export interface AdminAuditEntry {
  id: string;
  action: string;
  object_type: string;
  object_id: string | null;
  actor_role: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface AdminAuditList {
  items: AdminAuditEntry[];
}

export interface AdminPayment {
  public_id: string;
  user_name: string | null;
  plan_code: string;
  provider: string;
  status: string;
  amount_kopecks: number;
  currency: string;
  created_at: string;
  paid_at: string | null;
}

export interface AdminPaymentList {
  items: AdminPayment[];
}

export interface AdminPaymentEvent {
  provider_event_id: string;
  event_type: string;
  status: string;
  signature_valid: boolean;
  processed_at: string | null;
  error: string | null;
  created_at: string;
}

export interface AdminPaymentDetail {
  order: BillingOrder;
  payment_id: string | null;
  events: AdminPaymentEvent[];
}

