import Link from "next/link";

export function Wordmark({ compact = false }: { compact?: boolean }) {
  return (
    <Link href="/" className="wordmark" aria-label="Zooffer — на главную">
      <span className="wordmark-mark" aria-hidden="true">
        <svg width="21" height="21" viewBox="0 0 24 24" fill="none">
          <path
            d="M5.3 11.4c1.8 0 3.2-1.8 3.2-3.7S7.1 4 5.3 4 2 5.8 2 7.7s1.5 3.7 3.3 3.7Zm13.4 0c1.8 0 3.3-1.8 3.3-3.7S20.5 4 18.7 4s-3.2 1.8-3.2 3.7 1.4 3.7 3.2 3.7ZM12 7.8c2.1 0 3.8-1.6 3.8-3.5S14.1.8 12 .8 8.2 2.4 8.2 4.3 9.9 7.8 12 7.8Zm-5.9 4.7c-2.2 0-4 1.4-4 3.4 0 1.8 1.5 3 3.2 3 1.1 0 1.8-.5 2.7-.5s1.6.5 2.7.5c1.7 0 3.2-1.2 3.2-3 0-2-1.8-3.4-4-3.4H6.1Zm11.8 0c-1.4 0-2.7.5-3.6 1.3.8 1 1.2 2.2 1.1 3.5.4.1.9.1 1.4.1 1.1 0 1.8-.5 2.7-.5s1.6.5 2.7.5c1.7 0 3.2-1.2 3.2-3 0-2-1.8-3.4-4-3.4h-3.5Z"
            fill="currentColor"
          />
        </svg>
      </span>
      {!compact && <span>zooffer</span>}
    </Link>
  );
}
