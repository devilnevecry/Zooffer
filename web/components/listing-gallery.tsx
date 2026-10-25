"use client";

import { useState } from "react";

import type { PhotoView } from "@/lib/types";

import { ArrowIcon, CloseIcon, PawIcon } from "./icons";
import { Modal } from "./modal";

export function ListingGallery({ photos, title }: { photos: PhotoView[]; title: string }) {
  const [active, setActive] = useState(0);
  const [lightbox, setLightbox] = useState(false);
  const index = photos.length > 0 ? Math.min(active, photos.length - 1) : 0;
  const current = photos[index];

  if (!current) {
    return (
      <div className="gallery-main gallery-empty">
        <PawIcon width={54} height={54} />
        <p>Фотографии пока не добавлены</p>
      </div>
    );
  }

  const go = (direction: -1 | 1) => {
    setActive((value) => {
      const from = photos.length > 0 ? Math.min(value, photos.length - 1) : 0;
      return (from + direction + photos.length) % photos.length;
    });
  };

  return (
    <div className="gallery">
      <div className="gallery-main">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={current.url}
          alt={current.alt ?? title}
          width={current.width}
          height={current.height}
        />
        <button
          type="button"
          className="gallery-open"
          onClick={() => setLightbox(true)}
          aria-label="Открыть фотографию на весь экран"
        />
        {photos.length > 1 && (
          <div className="gallery-arrows">
            <button
              type="button"
              className="round-action"
              onClick={() => go(-1)}
              aria-label="Предыдущее фото"
            >
              <ArrowIcon style={{ transform: "rotate(180deg)" }} />
            </button>
            <button
              type="button"
              className="round-action"
              onClick={() => go(1)}
              aria-label="Следующее фото"
            >
              <ArrowIcon />
            </button>
          </div>
        )}
        <span className="gallery-count">
          {index + 1} / {photos.length}
        </span>
      </div>
      {photos.length > 1 && (
        <div className="gallery-thumbs" aria-label="Фотографии объявления">
          {photos.map((photo, photoIndex) => (
            <button
              type="button"
              key={`${photo.url}-${photoIndex}`}
              aria-current={photoIndex === index}
              onClick={() => setActive(photoIndex)}
              aria-label={`Фотография ${photoIndex + 1}`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={photo.url} alt="" loading="lazy" />
            </button>
          ))}
        </div>
      )}
      <Modal open={lightbox} onClose={() => setLightbox(false)} title={title} wide>
        <div className="lightbox">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={current.url} alt={current.alt ?? title} />
          {photos.length > 1 && (
            <div className="lightbox-controls">
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => go(-1)}>
                <ArrowIcon style={{ transform: "rotate(180deg)" }} /> Назад
              </button>
              <span>
                {index + 1} из {photos.length}
              </span>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => go(1)}>
                Далее <ArrowIcon />
              </button>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}

export function CloseLightboxButton({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" className="icon-button" onClick={onClick} aria-label="Закрыть">
      <CloseIcon />
    </button>
  );
}
