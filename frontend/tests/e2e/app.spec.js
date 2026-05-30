import { expect, test } from '@playwright/test';

test('homepage has title MEERO and mic button', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('text=MEERO')).toBeVisible();
  // Check for mic button by role or aria-label
  const mic = page.locator('button[aria-label*="listen"], button[aria-label*="Start listening"]');
  await expect(mic.first()).toBeVisible();
});
