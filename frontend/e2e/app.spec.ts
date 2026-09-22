import type { Page } from "@playwright/test";
import { test, expect, TICKETS } from "./fixtures";

test.describe("Flow 1 — Affichage des projets", () => {
  test("les projets apparaissent dans la sidebar au chargement", async ({
    mockedPage,
  }) => {
    await mockedPage.goto("/");
    await expect(mockedPage.getByText("ide-core")).toBeVisible();
  });
});

// Depuis le pivot cockpit (ticket-065), le tableau des tickets occupe le
// centre : les mêmes titres apparaissent dans la liste latérale et dans le
// tableau. Une assertion qui ne dit pas de quelle région elle parle en trouve
// deux, et échoue en mode strict. Les régions sont nommées pour cela.
const lateral = (page: Pick<Page, "getByRole">) =>
  page.getByRole("complementary", { name: "Panneau latéral" });

test.describe("Flow 2 — Sélection d'un projet → liste de tickets", () => {
  test("cliquer sur un projet affiche ses tickets dans le panel Tickets", async ({
    mockedPage,
  }) => {
    await mockedPage.goto("/");

    // Click the project — triggers handleSelectProject → switches to tickets panel
    await mockedPage.getByText("ide-core").click();

    // Only check the "todo" ticket — "done" tickets are collapsed by default
    const todoTicket = TICKETS.find((t) => t.status === "todo")!;
    await expect(lateral(mockedPage).getByText(todoTicket.title)).toBeVisible();
  });
});

test.describe("Flow 3 — Création d'un projet", () => {
  test("remplir le formulaire et créer un projet", async ({ mockedPage }) => {
    await mockedPage.goto("/");

    // Open create project modal via the + button in the Projects panel header
    await mockedPage
      .getByRole("button", { name: "Créer un projet" })
      .first()
      .click();

    // Labels are "Nom *" and "Description" — use id selectors for reliability
    await mockedPage.locator("#project-name").fill("test-e2e");
    await mockedPage.locator("#project-description").fill("test");
    await mockedPage
      .getByRole("button", { name: "Créer", exact: true })
      .click();

    // Modal shows success screen — click "Continuer" to close it
    await mockedPage.getByRole("button", { name: /continuer/i }).click();

    // Modal closed; the "Créer" submit button is gone
    await expect(
      mockedPage.getByRole("button", { name: "Créer", exact: true }),
    ).not.toBeVisible();
    // The TicketList header shows the selected project name
    await expect(lateral(mockedPage).getByText("test-e2e").first()).toBeVisible();
  });
});

test.describe("Flow 4 — Création d'un ticket", () => {
  test("créer un ticket dans un projet sélectionné", async ({ mockedPage }) => {
    await mockedPage.goto("/");

    // Select project (auto-switches to tickets panel)
    await mockedPage.getByText("ide-core").click();

    // Open create ticket modal via the + button in the Tickets panel header
    await lateral(mockedPage)
      .getByRole("button", { name: "Créer un ticket" })
      .click();

    // Use id selector for the title input (label is "Titre *")
    await mockedPage.locator("#ticket-title").fill("Ma feature");
    await mockedPage
      .getByRole("button", { name: "Créer", exact: true })
      .click();

    // Modal closes, new ticket appears.
    // `exact: true` est indispensable ici : sans lui, "Créer" matche aussi
    // "Créer un ticket" — le bouton + de la sidebar, qui reste visible après
    // la fermeture de la modale. L'assertion devient alors instable, et
    // échoue selon l'instant où le re-render la surprend.
    await expect(
      mockedPage.getByRole("button", { name: "Créer", exact: true }),
    ).not.toBeVisible();
    // C'est le toast qui confirme la création, pas la liste : l'API est
    // doublée et renvoie toujours la même fixture, donc un rafraîchissement
    // ne fera jamais apparaître « Ma feature » dans la sidebar. L'assertion
    // d'origine n'était pas cadrée et tombait déjà sur ce toast sans le dire.
    await expect(
      mockedPage.getByText(/Ticket .*Ma feature.* créé/),
    ).toBeVisible();
  });
});

test.describe("Flow 5 — Ouverture de l'éditeur Monaco", () => {
  test("cliquer sur un ticket affiche son contenu dans l'éditeur", async ({
    mockedPage,
  }) => {
    await mockedPage.goto("/");

    // Select project
    await mockedPage.getByText("ide-core").click();

    // Click on the todo ticket
    const todoTicket = TICKETS.find((t) => t.status === "todo")!;
    await lateral(mockedPage).getByText(todoTicket.title).click();

    // Monaco editor should be visible
    const editor = mockedPage.locator(".monaco-editor");
    await expect(editor).toBeVisible({ timeout: 8000 });
  });
});
