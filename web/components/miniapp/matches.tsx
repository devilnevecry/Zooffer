"use client";

import Link from "next/link";

import { HeartIcon, PawIcon } from "../icons";
import { formatDate, sexLabel, speciesLabel } from "@/lib/format";
import type { MatchList } from "@/lib/types";

import { MiniEmpty, MiniError, MiniLoading, MiniPageHead, useMiniApi } from "./ui";

export function MiniMatches() {
  const { data, loading, error, reload } = useMiniApi<MatchList>("/api/v1/matches");

  if (loading && !data) return <MiniLoading label="Загружаем совпадения…" />;
  if (error && !data) return <MiniError message={error} onRetry={reload} />;

  const items = data?.items ?? [];

  return (
    <div className="tg-stack">
      <MiniPageHead
        eyebrow="Совпадения"
        title="Это взаимно"
        lead="Только пары, где симпатия была взаимной. Односторонние лайки не открывают чат."
      />

      {items.length === 0 ? (
        <MiniEmpty
          title="Совпадений пока нет"
          text="Листайте карточки в подборе. Если владелец тоже ответит симпатией, здесь появится пара и откроется чат."
          href="/tg"
          action="Начать подбор"
        />
      ) : (
        <div className="match-grid tg-match-grid">
          {items.map((match) => (
            <article className="match-card" key={match.animal_public_id}>
              <div className="match-media">
                {match.primary_photo_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={match.primary_photo_url} alt={match.animal_name} />
                ) : (
                  <PawIcon width={42} height={42} />
                )}
                <span className="chip chip-live match-badge">
                  <HeartIcon width={11} height={11} fill="currentColor" /> Взаимно
                </span>
              </div>
              <div className="match-body">
                <span className="chip chip-brand">{speciesLabel(match.species)}</span>
                <h2>{match.animal_name}</h2>
                <p>
                  {match.breed || "Порода не указана"} · {sexLabel(match.sex)}
                </p>
                <p className="muted small">
                  {match.owner_display_name ?? "Владелец"} · {formatDate(match.created_at)}
                </p>
                <div className="btn-row">
                  {match.conversation_public_id && (
                    <Link
                      href={`/tg/chats/${match.conversation_public_id}`}
                      className="btn btn-primary btn-sm"
                    >
                      Открыть чат
                    </Link>
                  )}
                  {match.listing_slug && (
                    <Link
                      href={`/tg/listing/${match.listing_slug}`}
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
    </div>
  );
}
