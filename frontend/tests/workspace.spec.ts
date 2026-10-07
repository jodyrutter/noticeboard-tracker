import { test, expect, type Page } from "@playwright/test";

const plan = {
  id: 3,
  title: "Foundations of full-stack development",
  description:
    "Build confidence across the stack. Practice React fundamentals, API design, and working with relational data.",
  due_date: "2026-10-28",
  created_by: 1,
};
const plans = [
  plan,
  {
    ...plan,
    id: 4,
    title: "SQL & relational thinking",
    description:
      "Turn questions into queries. Explore joins, data modeling, and the stories behind the numbers.",
    due_date: "2026-11-04",
  },
  {
    ...plan,
    id: 5,
    title: "Working well, together",
    description:
      "A practical introduction to code reviews, clear communication, and collaborative development.",
    due_date: null,
  },
];
const trainees = [
  {
    id: 7,
    user_id: 8,
    name: "Alex Morgan",
    email: "alex@example.com",
    cohort_id: 1,
    cohort_name: "Autumn engineering",
    status: "ACTIVE",
    onboarding_date: "2026-10-01",
  },
  {
    id: 9,
    user_id: 10,
    name: "Jamie Rivera",
    email: "jamie@example.com",
    cohort_id: 1,
    cohort_name: "Autumn engineering",
    status: "ACTIVE",
    onboarding_date: "2026-10-01",
  },
  {
    id: 11,
    user_id: 12,
    name: "Sam Chen",
    email: "sam@example.com",
    cohort_id: 2,
    cohort_name: "Technology associates",
    status: "ACTIVE",
    onboarding_date: "2026-10-05",
  },
];

async function setup(page: Page, role = "MANAGER", signedIn = true) {
  const token = `header.${Buffer.from(JSON.stringify({ sid: "test-session", exp: Math.floor(Date.now() / 1000) + 1800 })).toString("base64url")}.test`;
  if (signedIn)
    await page.addInitScript(
      (t) =>
        localStorage.setItem(
          "noticeboard_auth",
          JSON.stringify({ token: t, email: "alex@example.com" }),
        ),
      token,
    );
  const writes: {
    path: string;
    body: Record<string, unknown>;
    method: string;
  }[] = [];
  await page.route("**/backend/**", async (route) => {
    const req = route.request(),
      path = new URL(req.url()).pathname.replace("/backend", "");
    if (req.method() !== "GET") {
      writes.push({
        path,
        body: req.postDataJSON() ?? {},
        method: req.method(),
      });
      if (path === "/api/logout") return route.fulfill({ status: 204 });
      if (req.method() === "DELETE")
        return route.fulfill({
          status: 409,
          json: {
            detail: "Cannot delete a plan with assignments or progress reports",
          },
        });
      return route.fulfill({
        status: path === "/api/login" ? 200 : 201,
        json:
          path === "/api/login"
            ? { access_token: token, token_type: "bearer" }
            : { id: 20, message: "Saved" },
      });
    }
    const data: Record<string, unknown> = {
      "/api/me": {
        user_id: 8,
        name: "Alex Morgan",
        email: "alex@example.com",
        role,
      },
      "/dashboard": {
        total_trainees: 24,
        active_trainees: 21,
        total_cohorts: 3,
        completed_reports: 32,
        in_progress_reports: 18,
        blocked_reports: 4,
        missing_reports: 7,
      },
      "/dashboard/trainees": trainees.map((t) => ({
        trainee_id: t.id,
        name: t.name,
        email: t.email,
        cohort: t.cohort_name,
        status: t.status,
      })),
      "/trainees": trainees,
      "/plans": plans,
      "/plans/3": plan,
      "/cohorts": [
        {
          id: 1,
          name: "Autumn engineering",
          start_date: "2026-10-01",
          end_date: "2026-12-20",
        },
        {
          id: 2,
          name: "Technology associates",
          start_date: "2026-10-05",
          end_date: null,
        },
      ],
      "/progress/plan/3": [
        {
          id: 1,
          trainee_id: 7,
          plan_id: 3,
          status: "IN_PROGRESS",
          comments:
            "Finished the React exercises. Working on API integration next.",
          submitted_at: "2026-10-06T12:00:00",
        },
      ],
      "/progress/trainee/7": [],
      "/notifications/8": [
        {
          id: 6,
          user_id: 8,
          message:
            "Your new learning plan is ready. Take a look at Foundations of full-stack development.",
          is_read: false,
          created_at: "2026-10-06T09:00:00",
        },
      ],
    };
    if (!(path in data))
      return route.fulfill({
        status: 404,
        json: { detail: `Unexpected test route: ${path}` },
      });
    return route.fulfill({ json: data[path] });
  });
  return writes;
}

test("manager overview, create, assign, edit and protected deletion", async ({
  page,
}) => {
  const writes = await setup(page);
  await page.goto("/app");
  await expect(
    page.getByRole("heading", { name: "Your team, moving forward." }),
  ).toBeVisible();
  await expect(page.getByText("24", { exact: true })).toBeVisible();
  await page.screenshot({
    path: "test-results/manager-overview.png",
    fullPage: true,
  });
  await page.getByRole("link", { name: "Training plans" }).click();
  await page.getByRole("button", { name: "＋ Create plan" }).click();
  await page.getByLabel("Plan title").fill("New plan");
  await page.getByLabel("What will they learn?").fill("Testing APIs");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Create plan", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(writes.find((w) => w.path === "/plans")?.body).toEqual({
    title: "New plan",
    description: "Testing APIs",
    due_date: null,
  });
  await page
    .getByRole("button", { name: `Open ${plan.title}`, exact: true })
    .click();
  await page.getByRole("button", { name: "Assign", exact: true }).click();
  await page.getByLabel("Trainee", { exact: true }).selectOption("7");
  await page.getByRole("button", { name: "Assign plan", exact: true }).click();
  await expect(page.getByText("Plan assigned successfully.")).toBeVisible();
  expect(
    writes.some((w) => w.path === "/plans/3/assign/trainee/7"),
  ).toBeTruthy();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByLabel("Plan title").fill("Revised plan");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(
    writes.some((w) => w.path === "/plans/3" && w.method === "PUT"),
  ).toBeTruthy();
  await page
    .getByRole("button", { name: `Open ${plan.title}`, exact: true })
    .click();
  await page.getByRole("button", { name: "Delete plan", exact: true }).click();
  await page.getByRole("button", { name: "Delete permanently" }).click();
  await expect(page.getByRole("alert")).toContainText("Cannot delete a plan");
});

test("HR enrollment, cohort assignment and cohort creation", async ({
  page,
}) => {
  const writes = await setup(page, "HR");
  await page.goto("/app/trainees");
  await expect(
    page.getByRole("heading", { name: "Trainees", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Overview", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "＋ Add trainee" }).click();
  await page.getByLabel("User account ID").fill("25");
  await page.getByLabel("Onboarding date").fill("2026-10-10");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Add trainee", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(
    writes.some((w) => w.path === "/trainees" && w.body.user_id === 25),
  ).toBeTruthy();
  await page.getByRole("button", { name: "View", exact: true }).first().click();
  await page.getByLabel("Cohort (optional)").selectOption("2");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(
    writes.some((w) => w.method === "PATCH" && w.body.cohort_id === 2),
  ).toBeTruthy();
  await page.getByRole("link", { name: "Cohorts", exact: true }).click();
  await page.getByRole("button", { name: "＋ Create cohort" }).click();
  await page.getByLabel("Cohort name").fill("Winter cohort");
  await page.getByLabel("Start date").fill("2026-12-01");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Create cohort", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(
    writes.some(
      (w) => w.path === "/cohorts" && w.body.name === "Winter cohort",
    ),
  ).toBeTruthy();
});

test("trainee progress, own notifications, profile and logout", async ({
  page,
}) => {
  const writes = await setup(page, "TRAINEE");
  await page.goto("/app");
  await expect(
    page.getByRole("heading", { name: "My learning plans" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Trainees", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: `Open ${plan.title}`, exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Edit", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Share a progress update" }).click();
  await page.getByLabel("Your update").fill("Completed the exercises.");
  await page.getByRole("button", { name: "Submit progress" }).click();
  await expect(
    page.getByText("Finished the React exercises.", { exact: false }),
  ).toBeVisible();
  expect(writes.find((w) => w.path === "/progress")?.body).toEqual({
    plan_id: 3,
    status: "IN_PROGRESS",
    comments: "Completed the exercises.",
  });
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("link", { name: "Notifications", exact: true }).click();
  await page.getByRole("button", { name: "Mark read", exact: true }).click();
  await expect
    .poll(() => writes.some((w) => w.path === "/notifications/6/read"))
    .toBeTruthy();
  await page.getByRole("link", { name: "My account", exact: true }).click();
  await expect(page.getByText("#8", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome back." }),
  ).toBeVisible();
  expect(writes.some((w) => w.path === "/api/logout")).toBeTruthy();
});

test("signup and signin", async ({ page }) => {
  await setup(page, "TRAINEE", false);
  await page.goto("/app/signup");
  await page.getByLabel("Full name").fill("Alex Morgan");
  await page.getByLabel("Email address").fill("alex@example.com");
  await page.getByLabel("Password", { exact: true }).fill("Testing!123");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Welcome back." }),
  ).toBeVisible();
  await page.getByLabel("Email address").fill("alex@example.com");
  await page.getByLabel("Password", { exact: true }).fill("Testing!123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "My learning plans" }),
  ).toBeVisible();
});

test("mobile navigation and no horizontal overflow", async ({ page }) => {
  await setup(page, "TRAINEE");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/app/plans");
  await expect(
    page.getByRole("heading", { name: "My learning plans" }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/trainee-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await page.getByRole("link", { name: "My account", exact: true }).click();
  await expect(page.getByRole("heading", { name: "My account" })).toBeVisible();
});

test("API errors, retry and session rejection", async ({ page }) => {
  await setup(page, "TRAINEE");
  let fail = true;
  await page.route("**/backend/plans", (route) =>
    route.fulfill(
      fail
        ? { status: 500, json: { detail: "Database unavailable" } }
        : { json: [] },
    ),
  );
  await page.goto("/app/plans");
  await expect(page.getByRole("alert")).toContainText("encountered a problem");
  fail = false;
  await page.getByRole("button", { name: "Try again", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Nothing here yet" }),
  ).toBeVisible();
  await page.route("**/backend/notifications/8", (route) =>
    route.fulfill({ status: 401, json: { detail: "Expired" } }),
  );
  await page.getByRole("link", { name: "Notifications", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome back." }),
  ).toBeVisible();
});

test("login rate limit is explained", async ({ page }) => {
  await setup(page, "TRAINEE", false);
  await page.route("**/backend/api/login", (route) =>
    route.fulfill({ status: 429, json: { error: "Rate limit exceeded" } }),
  );
  await page.goto("/app/signin");
  await page.getByLabel("Email address").fill("alex@example.com");
  await page.getByLabel("Password", { exact: true }).fill("Testing!123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Too many attempts");
  await page.screenshot({ path: "test-results/signin.png", fullPage: true });
});
