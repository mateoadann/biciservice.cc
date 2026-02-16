import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const PanelCard = ({ frame, delay, title, value, color }) => {
  const { fps } = useVideoConfig();
  const appear = spring({
    frame: frame - delay,
    fps,
    config: { damping: 200, stiffness: 140 }
  });

  return (
    <div
      style={{
        flex: 1,
        minHeight: 170,
        borderRadius: 26,
        border: "1px solid rgba(255,255,255,0.2)",
        background: "rgba(9, 16, 39, 0.65)",
        padding: 28,
        transform: `translateY(${interpolate(appear, [0, 1], [26, 0])}px)`,
        opacity: appear,
        boxShadow: "0 12px 22px rgba(0,0,0,0.25)"
      }}
    >
      <div style={{ color: "#C7D2FE", fontSize: 24, marginBottom: 12 }}>{title}</div>
      <div style={{ color: "white", fontSize: 56, fontWeight: 700 }}>{value}</div>
      <div
        style={{
          marginTop: 18,
          height: 10,
          borderRadius: 999,
          background: "rgba(255,255,255,0.16)",
          overflow: "hidden"
        }}
      >
        <div
          style={{
            width: `${interpolate(appear, [0, 1], [0, 100])}%`,
            height: "100%",
            background: color
          }}
        />
      </div>
    </div>
  );
};

export const DashboardDemo = () => {
  const frame = useCurrentFrame();
  const titleOpacity = interpolate(frame, [0, 24], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        fontFamily: "Space Grotesk, sans-serif",
        color: "white",
        background:
          "radial-gradient(circle at 15% 0%, rgba(31,76,255,0.35), transparent 35%), radial-gradient(circle at 100% 100%, rgba(25,179,107,0.3), transparent 42%), #0A1226",
        padding: 54
      }}
    >
      <div
        style={{
          borderRadius: 32,
          border: "1px solid rgba(255,255,255,0.16)",
          height: "100%",
          background: "linear-gradient(140deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))",
          padding: 44,
          display: "flex",
          flexDirection: "column",
          gap: 28
        }}
      >
        <div style={{ opacity: titleOpacity }}>
          <div style={{ fontSize: 24, letterSpacing: 3, textTransform: "uppercase", color: "#8DA2FF" }}>
            biciservice.cc
          </div>
          <div style={{ marginTop: 8, fontSize: 64, fontWeight: 700 }}>Dashboard operativo en tiempo real</div>
        </div>

        <div style={{ display: "flex", gap: 18 }}>
          <PanelCard frame={frame} delay={20} title="Trabajos activos" value="31" color="#1F4CFF" />
          <PanelCard frame={frame} delay={28} title="Listos para retiro" value="12" color="#19B36B" />
          <PanelCard frame={frame} delay={36} title="Pendientes de stock" value="4" color="#FF8C2B" />
        </div>

        <div
          style={{
            flex: 1,
            borderRadius: 26,
            border: "1px solid rgba(255,255,255,0.2)",
            background: "rgba(6, 10, 25, 0.68)",
            padding: 24,
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 18
          }}
        >
          {[
            ["Open", 22, "#90A8FF"],
            ["In progress", 55, "#1F4CFF"],
            ["Ready", 80, "#19B36B"],
            ["Closed", 96, "#FF8C2B"]
          ].map(([label, amount, color], idx) => {
            const start = 48 + idx * 6;
            const progress = spring({ frame: frame - start, fps: 30 });
            return (
              <div key={label} style={{ alignSelf: "center" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8, fontSize: 23 }}>
                  <span style={{ color: "#DCE4FF" }}>{label}</span>
                  <span style={{ color }}>{amount}%</span>
                </div>
                <div style={{ height: 10, borderRadius: 999, background: "rgba(255,255,255,0.15)", overflow: "hidden" }}>
                  <div
                    style={{
                      width: `${interpolate(progress, [0, 1], [0, amount])}%`,
                      height: "100%",
                      background: color
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
