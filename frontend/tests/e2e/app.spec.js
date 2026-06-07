import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('http://localhost:8000/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body = { status: 'ok' };

    if (path === '/model/status') {
      body = {
        neural_net: { enabled: true, loaded: true },
        gguf_llm: { enabled: false, loaded: false, status: 'error' },
      };
    } else if (path === '/debug/health') {
      body = { status: 'ok', web_safe_mode: true };
    } else if (path === '/settings') {
      body = { show_history: true };
    } else if (path === '/command') {
      body = {
        response: 'Mock response.',
        action_status: 'success',
        sentiment: 'neutral',
      };
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });
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
  await expect(page.getByText('Mock response.').first()).toBeVisible();

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

test('typed fallback remains visible when speech is unavailable and preference is disabled', async ({ page }) => {
  await page.addInitScript(() => {
    delete window.SpeechRecognition;
    delete window.webkitSpeechRecognition;
  });
  await page.route('http://localhost:8000/settings', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ text_input_enabled: false }),
    });
  });

  await page.reload();

  await expect(page.getByLabel('Type command')).toBeVisible({ timeout: 8000 });
  await expect(page.getByText(/Speech recognition is not available/i)).toBeVisible();
});
