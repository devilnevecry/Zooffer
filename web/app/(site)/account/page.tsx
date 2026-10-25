import Link from "next/link";

import { ArrowIcon, BellIcon, ChatIcon, HeartIcon, PawIcon, PlusIcon } from "@/components/icons";
import { StatusChip } from "@/components/status-chip";
import { serverFetch } from "@/lib/api";
import { requireMe } from "@/lib/auth-server";
import { formatDateTime, formatListingPrice } from "@/lib/format";
import type {
  AnimalList,
  ConversationSummary,
  FavoriteList,
  NotificationList,
  OwnerListing,
} from "@/lib/types";

interface ConversationList {
  items: ConversationSummary[];
}

export default async function AccountOverviewPage() {
  const me = await requireMe();
  const [listings, animals, favorites, conversations, notifications] = await Promise.all([
    serverFetch<OwnerListing[]>("/api/v1/listings", { allow401: true }),
    serverFetch<AnimalList>("/api/v1/animals", { allow401: true }),
    serverFetch<FavoriteList>("/api/v1/favorites", { allow401: true }),
    serverFetch<ConversationList>("/api/v1/conversations", { allow401: true }),
    serverFetch<NotificationList>("/api/v1/notifications?limit=5", { allow401: true }),
  ]);

  const ownListings = listings ?? [];
  const ownAnimals = animals?.items ?? [];
  const favoriteItems = favorites?.items ?? [];
  const chats = conversations?.items ?? [];
  const unreadMessages = chats.reduce((sum, chat) => sum + chat.unread_count, 0);
  const published = ownListings.filter((listing) => listing.status === "published").length;
  const pending = ownListings.filter((listing) => listing.status === "pending_moderation").length;
  const unreadNotifications = notifications?.unread_count ?? 0;
  const recent = ownListings.slice(0, 4);

  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Личный кабинет</span>
          <h1>Здравствуйте, {me.user.first_name ?? "с вами"}</h1>
          <p className="muted">
            Здесь всё, что связано с вашими животными, объявлениями и перепиской.
          </p>
        </div>
        <Link href="/account/listings/new" className="btn btn-primary">
          <PlusIcon /> Разместить объявление
        </Link>
      </div>

      <div className="stat-row">
        <div className="stat">
          <strong>{ownAnimals.length}</strong>
          <span>животных в профиле</span>
        </div>
        <div className="stat">
          <strong>{published}</strong>
          <span>опубликовано</span>
        </div>
        <div className="stat">
          <strong>{pending}</strong>
          <span>на проверке</span>
        </div>
        <div className="stat">
          <strong>{favoriteItems.length}</strong>
          <span>в избранном</span>
        </div>
        <div className="stat">
          <strong>{unreadMessages}</strong>
          <span>непрочитанных сообщений</span>
        </div>
      </div>

      <div className="dashboard-grid">
        <section className="dashboard-card">
          <div className="card-head">
            <div>
              <h2>Ваши объявления</h2>
              <p>Статус и последние изменения</p>
            </div>
            <Link href="/account/listings" className="text-link">
              Все <ArrowIcon width={15} height={15} />
            </Link>
          </div>
          {recent.length > 0 ? (
            <div className="compact-list">
              {recent.map((listing) => (
                <Link
                  key={listing.public_id}
                  href={`/account/listings/${listing.public_id}/edit`}
                  className="compact-row"
                >
                  <span className="compact-icon">
                    <PawIcon width={18} height={18} />
                  </span>
                  <span className="grow">
                    <strong>{listing.title}</strong>
                    <small>
                      {formatListingPrice(
                        listing.purpose,
                        listing.price_kopecks,
                        listing.negotiable,
                      )}
                    </small>
                  </span>
                  <StatusChip status={listing.status} />
                </Link>
              ))}
            </div>
          ) : (
            <div className="dashboard-empty">
              <PawIcon width={32} height={32} />
              <p>Пока нет объявлений. Начните с анкеты животного.</p>
              <Link href="/account/listings/new" className="btn btn-secondary btn-sm">
                Создать объявление
              </Link>
            </div>
          )}
        </section>

        <section className="dashboard-card">
          <div className="card-head">
            <div>
              <h2>Новые события</h2>
              <p>Уведомления и сообщения</p>
            </div>
            <Link href="/account/notifications" className="text-link">
              Все <ArrowIcon width={15} height={15} />
            </Link>
          </div>
          {notifications?.items.length ? (
            <div className="compact-list">
              {notifications.items.slice(0, 4).map((item) => (
                <div className="compact-row" key={item.id}>
                  <span className="compact-icon">
                    <BellIcon width={18} height={18} />
                  </span>
                  <span className="grow">
                    <strong>{item.title}</strong>
                    <small>{formatDateTime(item.created_at)}</small>
                  </span>
                  {!item.read_at && <span className="unread-dot" aria-label="Не прочитано" />}
                </div>
              ))}
            </div>
          ) : (
            <div className="dashboard-empty">
              <BellIcon width={32} height={32} />
              <p>Новых уведомлений нет. Мы сообщим о совпадениях и сообщениях.</p>
            </div>
          )}
        </section>
      </div>

      <div className="quick-grid">
        <Link href="/discovery" className="quick-card">
          <HeartIcon />
          <div>
            <strong>Продолжить подбор</strong>
            <span>Смотреть новые карточки</span>
          </div>
          <ArrowIcon width={18} height={18} />
        </Link>
        <Link href="/account/chats" className="quick-card">
          <ChatIcon />
          <div>
            <strong>Перейти в сообщения</strong>
            <span>{unreadMessages > 0 ? `${unreadMessages} непрочитанных` : "Всё прочитано"}</span>
          </div>
          <ArrowIcon width={18} height={18} />
        </Link>
        <Link href="/account/favorites" className="quick-card">
          <HeartIcon />
          <div>
            <strong>Избранное</strong>
            <span>{favoriteItems.length} сохранённых объявлений</span>
          </div>
          <ArrowIcon width={18} height={18} />
        </Link>
      </div>

      {favoriteItems.length > 0 && (
        <section className="dashboard-section">
          <div className="section-head compact">
            <div>
              <h2>Сохранённое</h2>
              <p>Быстрый доступ к понравившимся животным</p>
            </div>
          </div>
          <div className="listing-grid">
            {favoriteItems.slice(0, 3).map((item) => (
              <Link href={`/listing/${item.slug}`} className="mini-favorite" key={item.public_id}>
                <span className="mini-favorite-mark">
                  <HeartIcon width={17} height={17} />
                </span>
                <strong>{item.animal_name}</strong>
                <span>{item.title}</span>
                <small>{formatListingPrice(item.purpose, item.price_kopecks)}</small>
              </Link>
            ))}
          </div>
        </section>
      )}

      <div className="notice account-notice">
        {unreadNotifications > 0
          ? `У вас ${unreadNotifications} непрочитанных уведомлений.`
          : "Аккаунт в порядке. Контакты и точный адрес не видны другим пользователям."}{" "}
        <Link href="/account/settings" className="text-link">
          Настройки приватности
        </Link>
      </div>
    </>
  );
}
