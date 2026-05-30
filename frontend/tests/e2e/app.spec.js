import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/');
});

test('app loads with title and primary voice control', async ({ page }) => {
  await expect(page.locator('text=MEERO')).toBeVisible();
  const mic = page.locator('button[aria-label*="listen"], button[aria-label*="Start listening"]');
  await expect(mic.first()).toBeVisible();
});

test('typed command flow records history and can clear it', async ({ page }) => {
  await expect(page.getByLabel('Type command')).toBeVisible({ timeout: 8000 });

  await page.getByLabel('Type command').fill('what time is it');
  await page.getByLabel('Send command').click();

  await expect(page.getByText('what time is it')).toBeVisible();
  await expect(page.getByText('I cannot reach the server.').first()).toBeVisible();

  await page.getByLabel('Clear conversation history').click();
  await expect(page.getByText('what time is it')).toHaveCount(0);
});

test('settings panel opens and shows offline-safe API status', async ({ page }) => {
  await expect(page.getByLabel('Open settings')).toBeVisible({ timeout: 8000 });

  await page.getByLabel('Open settings').click();

  await expect(page.getByText('Settings')).toBeVisible();
  await expect(page.getByText(/API: offline|API: online/)).toBeVisible();
  await expect(page.getByText(/Desktop: unknown|Desktop: safe|Desktop: local/)).toBeVisible();
  await expect(page.getByLabel('Refresh API status')).toBeVisible();
});

test('public health fallback or offline state does not crash the UI', async ({ page }) => {
  await expect(page.getByLabel('Open settings')).toBeVisible({ timeout: 8000 });

  await page.getByLabel('Open settings').click();
  await page.getByLabel('Refresh API status').click();

  await expect(page.getByText('Settings')).toBeVisible();
  await expect(page.getByText(/API: offline|API: online/)).toBeVisible();
});
