import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const TimelineStep = ({ frame, delay, title, description, done }) => {
  const { fps } = useVideoConfig();
  const progress = spring({
    frame: frame - delay,
    fps,
    config: { damping: 180, stiffness: 150 }
  });

  return (
    <div
      style={{
        padding: "18px 20px",
        borderRadius: 18,
        border: "1px solid rgba(255,255,255,0.2)",
        background: "rgba(8, 13, 34, 0.72)",
        display: "flex",
        gap: 14,
        alignItems: "flex-start",
        transform: `translateY(${interpolate(progress, [0, 1], [22, 0])}px)`,
        opacity: progress
      }}
    >
      <div
        style={{
          width: 30,
          height: 30,
          borderRadius: 999,
          background: done ? "#19B36B" : "rgba(255,255,255,0.25)",
          border: "2px solid rgba(255,255,255,0.25)",
          flexShrink: 0
        }}
      />
      <div>
        <div style={{ fontSize: 27, fontWeight: 700 }}>{title}</div>
        <div style={{ marginTop: 4, color: "#C6D4FF", fontSize: 21 }}>{description}</div>
      </div>
    </div>
  );
};

export const ClientesDemo = () => {
  const frame = useCurrentFrame();
  const titleReveal = interpolate(frame, [0, 28], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        fontFamily: "Space Grotesk, sans-serif",
        color: "white",
        background:
          "radial-gradient(circle at 0% 0%, rgba(25,179,107,0.25), transparent 32%), radial-gradient(circle at 100% 100%, rgba(31,76,255,0.28), transparent 35%), #081129",
        padding: 52
      }}
    >
      <div
        style={{
          borderRadius: 30,
          border: "1px solid rgba(255,255,255,0.16)",
          background: "linear-gradient(160deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03))",
          height: "100%",
          padding: 40,
          display: "grid",
          gridTemplateColumns: "0.95fr 1.05fr",
          gap: 26
        }}
      >
        <div style={{ opacity: titleReveal }}>
          <div style={{ fontSize: 24, letterSpacing: 2.5, color: "#8FDDB4", textTransform: "uppercase" }}>
            Flujo de clientes
          </div>
          <h1 style={{ margin: "10px 0 0", fontSize: 62, lineHeight: 1.05 }}>
            Desde la recepcion hasta la entrega
          </h1>
          <p style={{ marginTop: 16, fontSize: 24, lineHeight: 1.4, color: "#C6D4FF" }}>
            Cada paso queda registrado para que el equipo y el cliente sepan exactamente que esta pasando.
          </p>

          <div
            style={{
              marginTop: 26,
              borderRadius: 18,
              border: "1px solid rgba(255,255,255,0.2)",
              background: "rgba(8, 13, 34, 0.72)",
              padding: "16px 18px"
            }}
          >
            <div style={{ color: "#8FDDB4", fontSize: 19, fontWeight: 700, marginBottom: 8 }}>Cliente destacado</div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>Ana Perez - Specialized Epic</div>
            <div style={{ marginTop: 6, color: "#C6D4FF", fontSize: 21 }}>Trabajo: cambio de transmision y calibracion de frenos</div>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <TimelineStep
            frame={frame}
            delay={20}
            title="1. Alta de cliente"
            description="Se carga contacto, equipo y observaciones iniciales"
            done
          />
          <TimelineStep
            frame={frame}
            delay={32}
            title="2. Diagnostico"
            description="Se define presupuesto, repuestos y prioridad"
            done
          />
          <TimelineStep
            frame={frame}
            delay={44}
            title="3. Reparacion"
            description="Estado in_progress con tecnicos asignados"
            done={frame > 175}
          />
          <TimelineStep
            frame={frame}
            delay={56}
            title="4. Listo para retiro"
            description="Estado ready y aviso al cliente"
            done={frame > 228}
          />
          <TimelineStep
            frame={frame}
            delay={68}
            title="5. Cierre"
            description="Trabajo closed con historial y auditoria"
            done={frame > 286}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
};
