// main.tsx — point d'entrée de l'application.
// Monaco et ses workers ne sont pas importés ici : ils sont chargés à la
// demande quand l'utilisateur ouvre l'éditeur (ticket-355, ADR-012).
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { jetonDeSession } from "./lib/auth";

// Le jeton est en mémoire avant le premier rendu : les WebSocket ouvertes à la
// volée le trouvent. Un échec ne bloque pas l'interface, le bandeau prend le relais.
async function demarrer(): Promise<void> {
  await jetonDeSession().catch(() => "");
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

void demarrer();
