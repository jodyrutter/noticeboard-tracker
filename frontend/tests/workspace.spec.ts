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
      "/users/unenrolled": [
        { user_id: 25, email: "new@example.com", name: "New User" },
        { user_id: 26, email: "other@example.com", name: "Other User" },
      ],
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
  await expect(page.getByLabel("User account ID")).toHaveCount(0);
  await page.getByLabel("Onboarding date").fill("2026-10-10");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Add trainee", exact: true })
    .click();
  expect(writes.some((w) => w.path === "/trainees")).toBeFalsy();
  await expect(page.getByRole("dialog")).toBeVisible();

  await page.getByLabel("Search by email").fill("NEW@");
  await expect(
    page.getByRole("option", { name: "other@example.com", exact: false }),
  ).toHaveCount(0);
  await page.getByLabel("Available trainee emails").selectOption("25");
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
  await expect(
    page.getByLabel("How is it going?").locator("option"),
  ).toHaveText([
    "Choose…",
    "Not started",
    "In progress",
    "Completed",
    "Blocked — I need help",
  ]);
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

test("enrollment empty list and stale selection conflict", async ({ page }) => {
  await setup(page, "HR");
  await page.goto("/app/trainees");
  await page.getByRole("button", { name: "＋ Add trainee" }).click();
  await page.getByLabel("Search by email").fill("missing@");
  await expect(
    page.getByText("No available users match that email."),
  ).toBeVisible();
  await page.getByLabel("Search by email").fill("new@");
  await page.getByLabel("Available trainee emails").selectOption("25");
  await page.getByLabel("Onboarding date").fill("2026-10-10");
  await page.route("**/backend/trainees", (route) =>
    route.request().method() === "POST"
      ? route.fulfill({
          status: 409,
          json: { detail: "This user is already enrolled as a trainee." },
        })
      : route.fallback(),
  );
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Add trainee", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("already enrolled");
  await page.route("**/backend/users/unenrolled", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.getByRole("button", { name: "Refresh available users" }).click();
  await expect(
    page.getByRole("heading", { name: "No users awaiting enrollment" }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("dialog")
      .getByRole("button", { name: "Add trainee", exact: true }),
  ).toHaveCount(0);
});

test("HR promotion tables and role changes", async ({ page }) => {
  const writes = await setup(page, "HR");
  const promoted = {
    user_id: 25,
    name: "New User",
    email: "new@example.com",
    role: "TRAINEE",
  };
  const staff = [
    {
      user_id: 9,
      name: "Staff User",
      email: "staff@example.com",
      role: "MANAGER",
    },
  ];
  await page.route("**/backend/users/promotion", (route) =>
    route.fulfill({
      json: {
        staff: promoted.role === "TRAINEE" ? staff : [...staff, promoted],
        eligible: promoted.role === "TRAINEE" ? [promoted] : [],
      },
    }),
  );
  await page.route("**/backend/users/25/role", (route) => {
    promoted.role = route.request().postDataJSON().role;
    return route.fulfill({ json: promoted });
  });
  await page.goto("/app/promotion");
  await expect(
    page.getByRole("heading", { name: "Existing HR and Managers" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Eligible trainees" }),
  ).toBeVisible();
  await expect(page.getByRole("table")).toHaveCount(2);
  await page.screenshot({ path: "test-results/promotion.png", fullPage: true });
  for (const role of ["HR", "MANAGER", "TRAINEE"]) {
    await page
      .getByRole("button", { name: "Change role for new@example.com" })
      .click();
    await page.getByLabel("Account role").selectOption(role);
    await page.getByRole("button", { name: "Save role" }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(
      page.getByRole("row").filter({ hasText: "new@example.com" }),
    ).toContainText(role.toLowerCase());
  }
  await page.route("**/backend/users/25/role", (route) =>
    route.fulfill({
      status: 409,
      json: {
        detail: "This user has assigned training and cannot change roles.",
      },
    }),
  );
  await page
    .getByRole("button", { name: "Change role for new@example.com" })
    .click();
  await page.getByLabel("Account role").selectOption("HR");
  await page.getByRole("button", { name: "Save role" }).click();
  await expect(page.getByRole("alert")).toContainText("assigned training");
  expect(writes.filter((w) => w.path === "/api/signup")).toHaveLength(0);
});

for (const role of ["TRAINEE", "MANAGER"]) {
  test(`Promotion is hidden from ${role}`, async ({ page }) => {
    await setup(page, role);
    await page.goto("/app/promotion");
    await expect(
      page.getByRole("heading", {
        name:
          role === "MANAGER"
            ? "Your team, moving forward."
            : "My learning plans",
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Promotion", exact: true }),
    ).toHaveCount(0);
  });
}

test("trainee and progress status dropdowns use fixed values", async ({
  page,
}) => {
  await setup(page, "HR");
  await page.goto("/app/trainees");
  await page.getByRole("button", { name: "View", exact: true }).first().click();
  await expect(page.getByLabel("Status").locator("option")).toHaveText([
    "Choose…",
    "ACTIVE",
    "INACTIVE",
    "COMPLETED",
    "WITHDRAWN",
  ]);
  await page.getByLabel("Status").selectOption("WITHDRAWN");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("cohort checkbox picker adds, removes and keeps selections while searching", async ({
  page,
}) => {
  const writes = await setup(page, "HR");
  await page.goto("/app/cohorts");
  await page.getByRole("button", { name: "View cohort" }).first().click();
  await page.getByText("Choose members (2 selected)").click();
  await expect(
    page.getByRole("checkbox", { name: /Alex Morgan/ }),
  ).toBeChecked();
  await page.getByRole("checkbox", { name: /Jamie Rivera/ }).uncheck();
  await page.getByRole("checkbox", { name: /Sam Chen/ }).check();
  await page
    .getByRole("textbox", { name: "Search members by name or email…" })
    .fill("alex");
  await page.getByRole("button", { name: "Save members" }).click();
  await expect(page.getByText("Cohort members saved.")).toBeVisible();
  expect(writes.find((w) => w.path === "/cohorts/1/members")?.body).toEqual({
    add: [11],
    remove: [9],
  });
});

test("focus revalidation preserves open forms and throttles repeated focus", async ({
  page,
}) => {
  await setup(page, "MANAGER");
  await page.clock.install();
  let initialReads = 0;
  await page.route("**/backend/api/me", (route) => {
    initialReads++;
    return route.fallback();
  });
  await page.goto("/app/plans");
  await page.getByRole("button", { name: "＋ Create plan" }).click();
  await page.getByLabel("Plan title").fill("Unsaved draft");
  expect(initialReads).toBe(1);
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  expect(initialReads).toBe(1);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let checks = 0;
  await page.route("**/backend/api/me", async (route) => {
    checks++;
    await gate;
    await route.fallback();
  });
  await page.clock.fastForward(61000);
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect.poll(() => checks).toBe(1);
  await expect(page.getByLabel("Plan title")).toHaveValue("Unsaved draft");
  const response = page.waitForResponse("**/backend/api/me");
  release();
  await response;
  await expect(page.getByLabel("Plan title")).toHaveValue("Unsaved draft");
  await page.evaluate(() => {
    window.dispatchEvent(new Event("focus"));
    window.dispatchEvent(new Event("focus"));
  });
  expect(checks).toBe(1);
});

test("duplicate plan assignment displays useful conflict", async ({ page }) => {
  await setup(page, "MANAGER");
  await page.route("**/backend/plans/3/assign/trainee/7", (route) =>
    route.fulfill({
      status: 409,
      json: { detail: "This plan is already assigned to this trainee." },
    }),
  );
  await page.goto("/app/plans");
  await page
    .getByRole("button", { name: `Open ${plan.title}`, exact: true })
    .click();
  await page.getByRole("button", { name: "Assign", exact: true }).click();
  await page.getByLabel("Trainee", { exact: true }).selectOption("7");
  await page.getByRole("button", { name: "Assign plan", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("already assigned");
});
