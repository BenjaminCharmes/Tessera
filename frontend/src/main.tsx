// main.tsx — point d'entrée de l'application.
// Monaco et ses workers ne sont pas importés ici : ils sont chargés à la
// demande quand l'utilisateur ouvre l'éditeur (ticket-355, ADR-012).
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
