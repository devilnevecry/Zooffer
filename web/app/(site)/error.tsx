"use client";

import Link from "next/link";

export default function SiteError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="page">
      <div className="container">
        <div className="empty-state">
          <span className="eyebrow">Ошибка</span>
          <h1>Что-то пошло не так</h1>
          <p>
            Мы не смогли загрузить эту страницу. Попробуйте ещё раз — данные не потеряны. Если
            ошибка повторяется, напишите в поддержку.
          </p>
          <div className="btn-row">
            <button type="button" className="btn btn-primary" onClick={reset}>
              Попробовать снова
            </button>
            <Link href="/" className="btn btn-secondary">
              На главную
            </Link>
            <Link href="/support" className="btn btn-ghost">
              Поддержка
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
