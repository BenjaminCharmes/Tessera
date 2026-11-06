import { useEffect, useState } from "react";
import { jetonEnCache } from "../lib/auth";
import { BASE, send } from "../lib/http";

export interface ImageChargee {
  /** Ce qu'on met dans `<img src>` ; `null` tant qu'il n'y a rien à afficher. */
  src: string | null;
  /** Vrai quand l'image n'a pas pu être lue (la requête a échoué). */
  echec: boolean;
}

/**
 * Adresse affichable d'une image servie par l'API (`chemin` relatif à `/api/v1`).
 *
 * Sans jeton, l'adresse directe suffit. Avec un jeton de session, un `<img>` ne
 * peut pas porter d'en-tête et le backend refuse `?token=` hors WebSocket :
 * l'image passe par le client HTTP commun (Bearer), puis par une URL objet
 * révoquée au démontage ou au changement de chemin.
 */
export function useImageAuthentifiee(chemin: string | null): ImageChargee {
  const jeton = jetonEnCache();
  const [objet, setObjet] = useState<{ chemin: string; url: string } | null>(null);
  const [echoue, setEchoue] = useState<string | null>(null);

  useEffect(() => {
    if (chemin === null || !jeton) return;
    let annule = false;
    let url: string | null = null;
    send(chemin)
      .then((reponse) => reponse.blob())
      .then((blob) => {
        if (annule) return;
        url = URL.createObjectURL(blob);
        setObjet({ chemin, url });
      })
      .catch(() => {
        if (!annule) setEchoue(chemin);
      });
    return () => {
      annule = true;
      if (url !== null) URL.revokeObjectURL(url);
    };
  }, [chemin, jeton]);

  if (chemin === null) return { src: null, echec: false };
  if (!jeton) return { src: `${BASE}${chemin}`, echec: false };
  return { src: objet?.chemin === chemin ? objet.url : null, echec: echoue === chemin };
}
