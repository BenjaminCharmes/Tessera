import type { ReactElement, SVGProps } from "react";

/**
 * Le jeu d'icônes de l'application — ticket-067.
 *
 * Avant ce module, les affordances étaient des glyphes collés dans le JSX :
 * `⚡ ✅ ⚠ ✕ ↗ ◈ ●`, empruntés à autant de jeux différents. Un glyphe ne se
 * contrôle ni en taille, ni en épaisseur de trait, ni en alignement optique, et
 * son rendu dépend de la police installée sur la machine — le même écran ne se
 * ressemblait pas d'un poste à l'autre.
 *
 * Toutes les icônes ci-dessous partagent la même grille de 24, le même trait et
 * les mêmes jointures, et héritent de la couleur du texte. C'est ce qui les
 * fait lire comme une famille plutôt que comme une collection.
 *
 * Pour en ajouter une : la dessiner sur cette grille, au même trait. Si le
 * dessin demande un trait plus épais pour être lisible, c'est qu'il est trop
 * détaillé pour la taille à laquelle il sera vu.
 */
type IconProps = Omit<SVGProps<SVGSVGElement>, "children"> & {
  /** Côté du carré, en pixels. 14 dans un badge, 16 en ligne, 20 en navigation. */
  size?: number;
};

function Icon({ size = 16, children, ...props }: IconProps & { children: ReactElement | ReactElement[] }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  );
}

export const IconCheck = (p: IconProps) => (
  <Icon {...p}>
    <path d="m5 12.5 4.5 4.5L19 7.5" />
  </Icon>
);

export const IconCross = (p: IconProps) => (
  <Icon {...p}>
    <path d="M6.5 6.5l11 11M17.5 6.5l-11 11" />
  </Icon>
);

export const IconAlert = (p: IconProps) => (
  <Icon {...p}>
    <path d="M12 4.5 21 19.5H3z" />
    <path d="M12 10v4M12 17h.01" />
  </Icon>
);

export const IconInfo = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 11v5.5M12 7.8h.01" />
  </Icon>
);

export const IconClock = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7.5V12l3 1.8" />
  </Icon>
);

export const IconBolt = (p: IconProps) => (
  <Icon {...p}>
    <path d="M13 3 5.5 13.5H11l-.5 7.5L18.5 10.5H13z" />
  </Icon>
);

export const IconPlus = (p: IconProps) => (
  <Icon {...p}>
    <path d="M12 5.5v13M5.5 12h13" />
  </Icon>
);

export const IconBoard = (p: IconProps) => (
  <Icon {...p}>
    <rect x="3.5" y="4.5" width="17" height="15" rx="2" />
    <path d="M9 4.5v15M15 4.5v15" />
  </Icon>
);

export const IconExternal = (p: IconProps) => (
  <Icon {...p}>
    <path d="M14 4.5h5.5V10" />
    <path d="M19.5 4.5 11 13" />
    <path d="M18 14v4.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10" />
  </Icon>
);

export const IconProject = (p: IconProps) => (
  <Icon {...p}>
    <path d="M3 7.5 12 3l9 4.5-9 4.5z" />
    <path d="M3 12.5 12 17l9-4.5" />
  </Icon>
);

export const IconChevronRight = (p: IconProps) => (
  <Icon {...p}>
    <path d="m9.5 5.5 7 6.5-7 6.5" />
  </Icon>
);

export const IconChevronDown = (p: IconProps) => (
  <Icon {...p}>
    <path d="m5.5 9.5 6.5 7 6.5-7" />
  </Icon>
);

export const IconDot = ({ size = 8, ...p }: IconProps) => (
  <svg
    viewBox="0 0 8 8"
    width={size}
    height={size}
    aria-hidden="true"
    focusable="false"
    {...p}
  >
    <circle cx="4" cy="4" r="3" fill="currentColor" />
  </svg>
);

export const IconPlay = (p: IconProps) => (
  <Icon {...p}>
    <path d="M8 5.5 18 12 8 18.5z" />
  </Icon>
);

export const IconRefresh = (p: IconProps) => (
  <Icon {...p}>
    <path d="M20 12a8 8 0 1 1-2.4-5.7" />
    <path d="M20.5 4v4h-4" />
  </Icon>
);

export const IconDownload = (p: IconProps) => (
  <Icon {...p}>
    <path d="M12 4v11" />
    <path d="m7.5 10.5 4.5 4.5 4.5-4.5" />
    <path d="M4.5 19.5h15" />
  </Icon>
);

export const IconMerge = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="7" cy="6" r="2.5" />
    <circle cx="7" cy="18" r="2.5" />
    <circle cx="17" cy="12" r="2.5" />
    <path d="M7 8.5v7" />
    <path d="M9.5 6h2.5a2.5 2.5 0 0 1 2.5 2.5V10" />
  </Icon>
);

export const IconBlocked = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="m6.5 6.5 11 11" />
  </Icon>
);

export const IconSettings = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="3" />
    <path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M5.6 5.6l1.8 1.8M16.6 16.6l1.8 1.8M18.4 5.6l-1.8 1.8M7.4 16.6l-1.8 1.8" />
  </Icon>
);

export const IconDiff = (p: IconProps) => (
  <Icon {...p}>
    <path d="M7 4.5v7M3.5 8h7" />
    <path d="M13.5 16h7" />
    <path d="M4 20 20 4" />
  </Icon>
);

export const IconQueue = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4 6.5h10M4 12h10M4 17.5h10" />
    <path d="M18.5 9v6M15.5 12h6" />
  </Icon>
);

// Les huit icônes du rail de navigation (ticket-251). Elles vivaient dans
// NavRail sur une grille locale identique à celle-ci : deux jeux d'une même
// famille finissent par diverger, et un test interdit désormais tout `<svg>`
// hors de design/.

export const IconLayers = (p: IconProps) => (
  <Icon {...p}>
    <path d="M3 7.5 12 3l9 4.5-9 4.5z" />
    <path d="M3 12.5 12 17l9-4.5" />
    <path d="M3 17 12 21.5 21 17" />
  </Icon>
);

export const IconList = (p: IconProps) => (
  <Icon {...p}>
    <path d="M8 6h12M8 12h12M8 18h12" />
    <path d="M4 6h.01M4 12h.01M4 18h.01" />
  </Icon>
);

export const IconFolder = (p: IconProps) => (
  <Icon {...p}>
    <path d="M3 6.5A1.5 1.5 0 0 1 4.5 5h4l2 2.5h7A1.5 1.5 0 0 1 19 9v8.5A1.5 1.5 0 0 1 17.5 19h-13A1.5 1.5 0 0 1 3 17.5z" />
  </Icon>
);

export const IconHistory = (p: IconProps) => (
  <Icon {...p}>
    <path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1" />
    <path d="M3 4v4h4" />
    <path d="M12 7.5V12l3 1.8" />
  </Icon>
);

export const IconRobot = (p: IconProps) => (
  <Icon {...p}>
    <rect x="4.5" y="7.5" width="15" height="12" rx="2.5" />
    <path d="M12 3.5v4" />
    <path d="M9 12.5h.01M15 12.5h.01" />
    <path d="M9.5 16h5" />
  </Icon>
);

export const IconRadar = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="3" />
    <path d="M12 3v3M12 18v3M3 12h3M18 12h3" />
    <path d="M5.6 5.6 7.8 7.8M16.2 16.2l2.2 2.2M18.4 5.6 16.2 7.8M7.8 16.2l-2.2 2.2" />
  </Icon>
);

export const IconChart = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
  </Icon>
);

export const IconChat = (p: IconProps) => (
  <Icon {...p}>
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </Icon>
);
