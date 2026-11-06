/** Une ligne du journal du superviseur, telle que `GET /supervision/recap` la rend (ticket-860). */
export interface LigneRecap {
  /** Jour ISO (`AAAA-MM-JJ`). */
  jour: string;
  action: string;
  cible: string;
  /** SHA du commit de l'intervention, entier : l'écran n'en montre que le début. */
  sha: string;
  resume: string;
}

/** Un cas « À toi » resté ouvert, avec la recommandation du superviseur. */
export interface CasRecap {
  jour: string;
  cible: string;
  recommandation: string;
}

export interface RecapSupervision {
  depuis: string | null;
  lignes: LigneRecap[];
  a_toi: CasRecap[];
}
