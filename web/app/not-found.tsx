import Link from "next/link";

export default function NotFound() {
  return (
    <main className="standalone-page">
      <div className="empty-state">
        <span className="eyebrow">404</span>
        <h1>Страница не найдена</h1>
        <p>
          Возможно, объявление снято, ссылка устарела или страница переехала. Начните с подбора или
          поиска.
        </p>
        <div className="btn-row">
          <Link href="/" className="btn btn-primary">
            На главную
          </Link>
          <Link href="/search" className="btn btn-secondary">
            К поиску
          </Link>
          <Link href="/support" className="btn btn-ghost">
            Поддержка
          </Link>
        </div>
      </div>
    </main>
  );
}
