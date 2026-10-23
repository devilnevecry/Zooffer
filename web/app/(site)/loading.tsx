export default function SiteLoading() {
  return (
    <div className="page">
      <div className="container">
        <div className="skeleton-hero" aria-hidden="true">
          <span className="skeleton-line short" />
          <span className="skeleton-line title" />
          <span className="skeleton-line" />
          <span className="skeleton-line medium" />
        </div>
        <div className="skeleton-grid" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, index) => (
            <span className="skeleton-card" key={index} />
          ))}
        </div>
        <span className="sr-only" role="status">
          Загружаем страницу…
        </span>
      </div>
    </div>
  );
}
