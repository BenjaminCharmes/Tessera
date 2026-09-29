import { test as base } from "@playwright/test";
import type { Page } from "@playwright/test";

export const PROJECTS = [
  {
    id: "ide-core",
    name: "ide-core",
    path: "/workspace/ide-core",
    description: "L'IDE lui-même",
    active_agents: ["codeur"],
    stack: "Python/FastAPI + React",
    raw_claude_md: "# ide-core",
  },
];

export const TICKETS = [
  {
    id: "ticket-001",
    title: "Setup projet",
    type: "feat",
    status: "todo",
    priority: "medium",
    agent: "codeur",
    depends_on: [],
    created: "2026-06-20",
    github_issue_url: null,
    body: "# Setup\n\nContenu du ticket.",
    project_id: "ide-core",
    file_path: "/tmp/ticket-001.md",
  },
  {
    id: "ticket-002",
    title: "Modèles de données",
    type: "feat",
    status: "done",
    priority: "high",
    agent: "codeur",
    depends_on: [],
    created: "2026-06-20",
    github_issue_url: null,
    body: "# Modèles",
    project_id: "ide-core",
    file_path: "/tmp/ticket-002.md",
  },
];

export const NEW_PROJECT = {
  id: "test-e2e",
  name: "test-e2e",
  description: "test",
  active_agents: [],
  stack: null,
  raw_claude_md: "",
};

export const NEW_TICKET = {
  id: "ticket-new",
  title: "Ma feature",
  type: "feat",
  status: "todo",
  priority: "medium",
  agent: "codeur",
  depends_on: [],
  created: "2026-06-20",
  github_issue_url: null,
  body: "",
  project_id: "ide-core",
  file_path: "/tmp/ticket-new.md",
};

async function setupApiMocks(page: Page) {
  await page.route("/api/v1/projects", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: PROJECTS });
    } else if (route.request().method() === "POST") {
      const body = route.request().postDataJSON() as {
        name: string;
        description: string;
      };
      await route.fulfill({
        json: {
          project: {
            ...NEW_PROJECT,
            name: body.name,
            description: body.description,
          },
          agents_created: [],
        },
        status: 201,
      });
    } else {
      await route.continue();
    }
  });

  await page.route("/api/v1/projects/ide-core/tickets", async (route) => {
    if (route.request().method() === "GET") {
      // Depuis le ticket-210, la liste arrive avec les fichiers illisibles.
      await route.fulfill({ json: { tickets: TICKETS, unreadable: [] } });
    } else if (route.request().method() === "POST") {
      const body = route.request().postDataJSON() as { title: string };
      await route.fulfill({
        json: { ...NEW_TICKET, title: body.title },
        status: 201,
      });
    } else {
      await route.continue();
    }
  });

  await page.route("/api/v1/projects/test-e2e/tickets", async (route) => {
    await route.fulfill({ json: { tickets: [], unreadable: [] } });
  });

  await page.route("/api/v1/projects/ide-core/runs*", async (route) => {
    await route.fulfill({ json: [] });
  });

  await page.route("/api/v1/projects/test-e2e/runs*", async (route) => {
    await route.fulfill({ json: [] });
  });
}

export const test = base.extend<{ mockedPage: Page }>({
  mockedPage: async ({ page }, use) => {
    await setupApiMocks(page);
    await use(page);
  },
});

export { expect } from "@playwright/test";
