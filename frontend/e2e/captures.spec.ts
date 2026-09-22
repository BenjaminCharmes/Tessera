import { test } from "./fixtures";

/**
 * Captures de référence pour la migration Tailwind v4 — ticket-117.
 *
 * Une régression Tailwind est **visuelle** : `tsc`, Vitest et Playwright
 * peuvent rester verts pendant que la mise en page est cassée. Ces captures
 * sont prises avant la migration, puis après, et comparées à l'œil — c'est la
 * seule vérification qui porte sur ce qui change réellement.
 *
 * Elles ne sont pas un test : rien n'échoue ici. C'est un outil, gardé parce
 * qu'il resservira à la prochaine migration d'un moteur de style.
 */
const lateral = (page: { getByRole: Function }) =>
  page.getByRole("complementary", { name: "Panneau latéral" });

test.describe("Captures", () => {
  test("cockpit au chargement", async ({ mockedPage }) => {
    await mockedPage.goto("/");
    await mockedPage.getByText("ide-core").first().waitFor();
    await mockedPage.screenshot({
      path: `captures/${process.env.CAPTURE_TAG ?? "avant"}-cockpit.png`,
      fullPage: true,
    });
  });

  test("tickets d'un projet", async ({ mockedPage }) => {
    await mockedPage.goto("/");
    await lateral(mockedPage).getByText("ide-core").first().click();
    await mockedPage.waitForTimeout(500);
    await mockedPage.screenshot({
      path: `captures/${process.env.CAPTURE_TAG ?? "avant"}-tickets.png`,
      fullPage: true,
    });
  });
});
