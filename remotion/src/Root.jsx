import { Composition } from "remotion";
import { DashboardDemo } from "./compositions/DashboardDemo";
import { ClientesDemo } from "./compositions/ClientesDemo";

export const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="Dashboard"
        component={DashboardDemo}
        durationInFrames={360}
        fps={30}
        width={1280}
        height={720}
      />
      <Composition
        id="Clientes"
        component={ClientesDemo}
        durationInFrames={330}
        fps={30}
        width={1280}
        height={720}
      />
    </>
  );
};
