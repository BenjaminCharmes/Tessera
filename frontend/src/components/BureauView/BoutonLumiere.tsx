import Agrandi from "../../design/bureau/Agrandi";
import Interrupteur from "../../design/bureau/Interrupteur";

interface BoutonLumiereProps {
  /** Le nom de la salle ou du projet, pour le nom accessible. */
  salle: string;
  allume: boolean;
  onBasculer: () => void;
}

/** L'interrupteur d'une salle : un clic allume ou éteint ses plafonniers. */
export default function BoutonLumiere({ salle, allume, onBasculer }: BoutonLumiereProps) {
  return (
    <button
      type="button"
      aria-pressed={allume}
      aria-label={`${allume ? "Éteindre" : "Allumer"} la lumière : ${salle}`}
      title={allume ? "Éteindre la lumière" : "Allumer la lumière"}
      onClick={onBasculer}
      className="block cursor-pointer rounded-sm focus-violet"
    >
      <Agrandi>
        <Interrupteur allume={allume} />
      </Agrandi>
    </button>
  );
}
