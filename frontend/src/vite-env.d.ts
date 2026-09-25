/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Même valeur que `STATIC_TOKEN` côté backend (ticket-120). Déclarée dans
   * `frontend/.env.local`, jamais commitée : elle est inlinée dans le bundle.
   */
  readonly VITE_STATIC_TOKEN?: string;
}
