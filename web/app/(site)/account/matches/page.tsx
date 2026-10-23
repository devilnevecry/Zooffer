import type { Metadata } from "next";
import Link from "next/link";

import { ArrowIcon, HeartIcon, PawIcon } from "@/components/icons";
import { requireMe } from "@/lib/auth-server";
import { getMatches } from "@/lib/data";
import { formatDate, sexLabel, speciesLabel } from "@/lib/format";

export const metadata: Metadata = {
  title: "Взаимные совпадения",
  robots: { index: false, follow: false },
};

export default async function MatchesPage() {
  await requireMe("/account/matches");
  const matches = await getMatches();
  const items = matches?.items ?? [];

  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Совпадения</span>
          <h1>Взаимные совпадения</h1>
          <p className="muted">
            Здесь только пары, где симпатия была взаимной. Односторонние лайки не
            создают совпадения и не открывают чат.
          </p>
        </div>
        <Link href="/discovery" className="btn btn-secondary">
          Продолжить подбор <ArrowIcon width={16} height={16} />
        </Link>
      </div>

      {items.length === 0 ? (
        <div className="empty-state">
          <HeartIcon width={44} height={44} />
          <h2>Совпадений пока нет</h2>
          <p>
            Листайте карточки животных. Если владелец тоже ответит симпатией, здесь
            появится пара и откроется чат.
          </p>
          <Link href="/discovery" className="btn btn-primary">
            Начать подбор
          </Link>
        </div>
      ) : (
        <div className="match-grid">
          {items.map((match) => (
            <article className="match-card" key={match.animal_public_id}>
              <div className="match-media">
                {match.primary_photo_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={match.primary_photo_url} alt={match.animal_name} />
                ) : (
                  <PawIcon width={42} height={42} />
                )}
                <span className="chip chip-live match-badge">Взаимно</span>
              </div>
              <div className="match-body">
                <span className="chip chip-brand">{speciesLabel(match.species)}</span>
                <h2>{match.animal_name}</h2>
                <p>
                  {match.breed || "Порода не указана"} · {sexLabel(match.sex)}
                </p>
                <p className="muted">
                  {match.owner_display_name ?? "Владелец"} · {formatDate(match.created_at)}
                </p>
                <div className="btn-row">
                  {match.conversation_public_id && (
                    <Link
                      href={`/account/chats/${match.conversation_public_id}`}
                      className="btn btn-primary btn-sm"
                    >
                      Открыть чат
                    </Link>
                  )}
                  {match.listing_slug && (
                    <Link
                      href={`/listing/${match.listing_slug}`}
                      className="btn btn-secondary btn-sm"
                    >
                      Объявление
                    </Link>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
