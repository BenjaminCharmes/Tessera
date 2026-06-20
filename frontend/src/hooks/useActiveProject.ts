import { useState } from "react";
import type { Project, Ticket } from "../types/api";

interface ActiveProjectState {
  project: Project | null;
  ticket: Ticket | null;
  setProject: (project: Project | null) => void;
  setTicket: (ticket: Ticket | null) => void;
}

export function useActiveProject(): ActiveProjectState {
  const [project, setProjectState] = useState<Project | null>(null);
  const [ticket, setTicket] = useState<Ticket | null>(null);

  function setProject(p: Project | null) {
    setProjectState(p);
    setTicket(null);
  }

  return { project, ticket, setProject, setTicket };
}
