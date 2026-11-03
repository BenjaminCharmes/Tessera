import type { EtatBoite } from "../../lib/bureau/boiteAuxLettres";
import { boite } from "../../lib/bureau/sprites/objets";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

interface BoiteProps {
  etat: EtatBoite;
}

const dessin = memoise(boite);

/**
 * La boîte aux lettres, grille 24 × 24 (36 × 36 px ; ticket-727). S'il y a une PR, une
 * lettre dépasse de la fente et le drapeau se lève, dans le ton de son état : ambre
 * ouverte, bleu en CI, vert mergée, rouge refusée (ADR-026). Sans PR, ni l'un ni l'autre.
 */
export default function Boite({ etat }: BoiteProps) {
  return <SpriteSvg sprite={dessin(etat)} largeur={36} hauteur={36} data-sprite="boite" data-boite={etat} />;
}
