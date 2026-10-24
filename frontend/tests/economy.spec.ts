import { expect, test } from '@playwright/test';

test.describe('Agentropolis economy slice', () => {
  test('navigates the shell and exposes the live event log', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', e => errors.push(e.message));

    await page.goto('/economy/world', { waitUntil: 'networkidle', timeout: 30000 });
    await expect(page).toHaveTitle(/Agentropolis/);
    await expect(page.getByRole('main')).toBeVisible();

    await page.goto('/economy/negotiations', { waitUntil: 'networkidle', timeout: 30000 });
    await expect(page).toHaveURL(/\/economy\/negotiations$/);
    await expect(page.getByRole('heading', { name: 'Offers, counteroffers, consequences.' })).toBeVisible();
    await expect(page.getByRole('log', { name: 'Economy event stream' })).toBeVisible();

    const skipLink = page.getByRole('link', { name: 'Skip to main content' });
    await skipLink.focus();
    await expect(skipLink).toBeFocused();

    expect(errors).toEqual([]);
  });

  test('keeps the shock controls usable under reduced motion', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/economy/scenarios', { waitUntil: 'networkidle', timeout: 30000 });
    await expect(page.getByRole('heading', { name: 'Find the fault line.' })).toBeVisible();

    const bankruptcy = page.getByRole('button', { name: /Supplier bankruptcy/ });
    await expect(bankruptcy).toBeEnabled();
    await bankruptcy.click();
    await expect(page.getByText('LIVE CAUSE → EFFECT')).toBeVisible();
  });
});
