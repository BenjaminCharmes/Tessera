import { describe, expect, it } from "vitest";
import { heureDeReprise } from "./bureau/heureDeReprise";
import { notificationsPour, type Instantane } from "./notifications";
import type { RelevesDeQuota } from "./notifQuota";
import type { QuotaWindowReading } from "./quota";

const MAINTENANT = Date.parse("2026-10-27T09:00:00Z");
const REPRISE_SEMAINE = "2026-10-30T07:00:00Z";
const REPRISE_SESSION = "2026-10-27T13:00:00Z";

function releve(restant: number, resetsAt: string | null): QuotaWindowReading {
  return {
    status: "allowed",
    utilization: (100 - restant) / 100,
    resets_at: resetsAt,
    observed_at: "2026-10-27T09:00:00Z",
  };
}

function instantane(quota: RelevesDeQuota | undefined): Instantane {
  return { runs: [], etats: {}, quota, maintenant: MAINTENANT };
}

function semaine(restant: number, resetsAt: string | null = REPRISE_SEMAINE): RelevesDeQuota {
  return { seven_day: releve(restant, resetsAt) };
}

describe("notificationsPour — quota bas", () => {
  it("notifies the weekly window going from 11 % to 9 % left, with the resume time", () => {
    const notifs = notificationsPour(instantane(semaine(11)), instantane(semaine(9)));

    expect(notifs).toHaveLength(1);
    expect(notifs[0].type).toBe("quota_bas");
    expect(notifs[0].titre).toBe("Quota de la semaine bas");
    expect(notifs[0].corps).toContain("9 %");
    expect(notifs[0].corps).toContain(heureDeReprise(REPRISE_SEMAINE, MAINTENANT));
  });

  it("does not notify a second reading at 8 % in the same period", () => {
    const notifs = notificationsPour(instantane(semaine(9)), instantane(semaine(8)));
    expect(notifs).toEqual([]);
  });

  it("notifies the session and the week separately", () => {
    const avant = { five_hour: releve(40, REPRISE_SESSION), seven_day: releve(30, REPRISE_SEMAINE) };
    const session = { ...avant, five_hour: releve(8, REPRISE_SESSION) };
    const lesDeux = { ...session, seven_day: releve(9, REPRISE_SEMAINE) };

    const premiere = notificationsPour(instantane(avant), instantane(session));
    expect(premiere.map((n) => n.titre)).toEqual(["Quota de la session bas"]);

    const seconde = notificationsPour(instantane(session), instantane(lesDeux));
    expect(seconde.map((n) => n.titre)).toEqual(["Quota de la semaine bas"]);
  });

  it("notifies again once the window has started over and falls low anew", () => {
    const basse = semaine(8, REPRISE_SEMAINE);
    const nouvelle = semaine(7, "2026-11-06T07:00:00Z");
    expect(notificationsPour(instantane(basse), instantane(nouvelle))).toHaveLength(1);
  });

  it("does not notify at exactly 10 % left", () => {
    expect(notificationsPour(instantane(semaine(30)), instantane(semaine(10)))).toEqual([]);
  });

  it("does not notify when the quota was not read before", () => {
    expect(notificationsPour(instantane(undefined), instantane(semaine(5)))).toEqual([]);
  });

  it("says so when the resume time is unknown", () => {
    const [n] = notificationsPour(instantane(semaine(30)), instantane(semaine(5, null)));
    expect(n.corps).toContain("pas connue");
  });

  it("ignores windows other than the session and the week", () => {
    const avant = { seven_day_opus: releve(50, REPRISE_SEMAINE) };
    const apres = { seven_day_opus: releve(5, REPRISE_SEMAINE) };
    expect(notificationsPour(instantane(avant), instantane(apres))).toEqual([]);
  });
});
