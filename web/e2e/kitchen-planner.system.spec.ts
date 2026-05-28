import { expect, type Page, test } from "@playwright/test";

const uniqueLogin = (prefix: string) =>
  `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;

async function register(page: Page, login: string, password: string) {
  await page.goto("/");
  await page.getByRole("button", { name: "Зарегистрировать нового пользователя" }).click();
  await page.getByLabel("Логин").fill(login);
  await page.getByLabel("Пароль").fill(password);
  await page.getByRole("button", { name: "Создать аккаунт" }).click();
  await expect(page.getByRole("heading", { name: "Планировщик кухни" })).toBeVisible();
}

async function generateKitchen(page: Page) {
  await page.getByRole("button", { name: /Сгенерировать кухню/ }).click();
  await expect(page.getByRole("heading", { name: "Top view" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Front view" })).toBeVisible();
}

test("user can register, generate a kitchen, open saved sketches, and delete history item", async ({
  page,
}) => {
  const login = uniqueLogin("system-user");

  await register(page, login, "password123");
  await generateKitchen(page);

  await page.getByRole("button", { name: "Личный кабинет" }).click();
  await expect(page.getByRole("heading", { name: "История генераций" })).toBeVisible();
  await expect(page.getByText("Автоматических корректировок")).toBeVisible();

  await page.getByRole("button", { name: "Открыть эскизы" }).first().click();
  await expect(page.getByRole("heading", { name: "Front view" })).toBeVisible();

  await page.getByRole("button", { name: "Личный кабинет" }).click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Удалить генерацию" }).first().click();
  await expect(page.getByText("История пока пустая")).toBeVisible();
});

test("corner kitchen with lift upper cabinets produces side view", async ({ page }) => {
  const login = uniqueLogin("corner-user");

  await register(page, login, "password123");

  await page.getByLabel("Форма").selectOption("corner");
  await page.getByLabel("Ширина стороны 1, мм").fill("3000");
  await page.getByLabel("Ширина стороны 2, мм").fill("2300");
  await page.getByRole("button", { name: /Развернуть/ }).first().click();
  await page.getByLabel("Открывание верхних шкафов").selectOption("lift");

  await generateKitchen(page);
  await expect(page.getByRole("heading", { name: "Side view" })).toBeVisible();
});

test("planner is unavailable before authentication", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", {
      name: "Подбор кухонного гарнитура по правилам и ограничениям",
    })
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Планировщик кухни" })).toHaveCount(0);
});
