"use client";

export default function RootError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="standalone-page">
      <div className="empty-state">
        <span className="eyebrow">Ошибка</span>
        <h1>Сервис временно недоступен</h1>
        <p>
          Попробуйте обновить страницу. Если проблема сохраняется, вернитесь позже или
          напишите в поддержку.
        </p>
        <div className="btn-row">
          <button type="button" className="btn btn-primary" onClick={reset}>
            Обновить
          </button>
          <a href="/support" className="btn btn-secondary">
            Поддержка
          </a>
        </div>
      </div>
    </main>
  );
}
