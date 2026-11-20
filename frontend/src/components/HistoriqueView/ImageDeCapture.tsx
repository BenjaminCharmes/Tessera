import { useImageAuthentifiee } from "../../hooks/useImageAuthentifiee";
import { cheminDeCapture } from "../../lib/capturesDuRun";

interface ImageDeCaptureProps {
  projectId: string;
  ticketId: string;
  fichier: string;
  alt: string;
  className: string;
}

/** Une image de capture, chargée avec l'en-tête d'authentification : jamais de jeton dans l'URL. */
export default function ImageDeCapture({ projectId, ticketId, fichier, alt, className }: ImageDeCaptureProps) {
  const { src } = useImageAuthentifiee(cheminDeCapture(projectId, ticketId, fichier));
  if (src === null) return <div aria-hidden="true" className={`${className} bg-zinc-800`} />;
  return <img src={src} alt={alt} className={className} />;
}
