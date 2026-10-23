import { ImageResponse } from "next/og";

export const alt = "Zooffer — животные находят своих людей";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px",
          background: "linear-gradient(135deg, #082f5c 0%, #0b64c9 60%, #5fb4ff 100%)",
          color: "#ffffff",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <div
            style={{
              width: 84,
              height: 84,
              borderRadius: 22,
              background: "#ffffff",
              color: "#0b64c9",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 58,
              fontWeight: 800,
            }}
          >
            Z
          </div>
          <div style={{ fontSize: 38, fontWeight: 700, letterSpacing: -1 }}>Zooffer</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              fontSize: 76,
              fontWeight: 800,
              lineHeight: 1.02,
              letterSpacing: -2,
            }}
          >
            <div>Животные находят</div>
            <div>своих людей</div>
          </div>
          <div style={{ fontSize: 28, opacity: 0.86, maxWidth: 900 }}>
            Бережный подбор, живые объявления и безопасная переписка внутри платформы.
          </div>
        </div>
        <div style={{ display: "flex", gap: 14, fontSize: 22, opacity: 0.8 }}>
          <span>Продажа</span>
          <span>·</span>
          <span>Вязка</span>
          <span>·</span>
          <span>Племенное разведение</span>
          <span>·</span>
          <span>Пристройство</span>
        </div>
      </div>
    ),
    size,
  );
}
