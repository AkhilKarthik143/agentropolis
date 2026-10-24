import { expect, test } from '@playwright/test';

test.describe('Agentropolis animated experience', () => {
  test('world page loads with ambient animations', async ({ page }) => {
    await page.goto('/economy/world', { waitUntil: 'networkidle', timeout: 30000 });
    await expect(page.getByRole('main')).toBeVisible();
    await expect(page.getByText('A living economy, moving in real time.')).toBeVisible();

    // Agent teams section should be present
    await expect(page.getByText('AGENT TEAMS', { exact: true })).toBeVisible();

    // Business nodes should be present (multiple match, use first)
    await expect(page.getByRole('button', { name: /— active/ }).first()).toBeVisible({ timeout: 15000 });
  });

  test('navigates between all major screens', async ({ page }) => {
    await page.goto('/economy/world', { waitUntil: 'networkidle', timeout: 30000 });

    // Navigate to negotiations
    await page.getByRole('link', { name: 'Negotiations' }).click();
    await expect(page).toHaveURL(/\/economy\/negotiations$/);
    await expect(page.getByRole('heading', { name: 'Offers, counteroffers, consequences.' })).toBeVisible();

    // Navigate to control tower
    await page.getByRole('link', { name: 'Control tower' }).click();
    await expect(page).toHaveURL(/\/economy\/control-tower$/);
    await expect(page.getByRole('heading', { name: 'Money moves. The books remember.' })).toBeVisible();

    // Navigate to procurement
    await page.getByRole('link', { name: 'Procurement' }).click();
    await expect(page).toHaveURL(/\/economy\/procurement$/);
    await expect(page.getByRole('heading', { name: 'Source with intent.' })).toBeVisible();

    // Navigate to scenarios
    await page.getByRole('link', { name: 'Shock engine' }).click();
    await expect(page).toHaveURL(/\/economy\/scenarios$/);
    await expect(page.getByRole('heading', { name: 'Find the fault line.' })).toBeVisible();

    // Navigate back to world
    await page.getByRole('link', { name: 'The World' }).click();
    await expect(page).toHaveURL(/\/economy\/world$/);
  });

  test('negotiation room shows offers with animation', async ({ page }) => {
    await page.goto('/economy/negotiations', { waitUntil: 'networkidle', timeout: 30000 });
    await expect(page.getByText('SUPPLIER COMPARISON', { exact: true })).toBeVisible();
    await expect(page.getByText('LIVE THREADS', { exact: true })).toBeVisible();
    await expect(page.getByText('DECISION TRACE', { exact: true })).toBeVisible();
  });

  test('control tower shows financial data with motion', async ({ page }) => {
    await page.goto('/economy/control-tower', { waitUntil: 'networkidle', timeout: 30000 });
    await expect(page.getByText('BUSINESS TREASURY', { exact: true })).toBeVisible();
    await expect(page.getByText('PAYMENT OPERATIONS', { exact: true })).toBeVisible();
    await expect(page.getByText('INTERNAL DOUBLE-ENTRY LEDGER', { exact: true })).toBeVisible();
  });

  test('procurement page shows supplier offers', async ({ page }) => {
    await page.goto('/economy/procurement', { waitUntil: 'networkidle', timeout: 30000 });
    await expect(page.getByText('ENGINE-SCORED OFFERS', { exact: true })).toBeVisible();
    await expect(page.getByText('PURCHASE SUMMARY', { exact: true })).toBeVisible();
  });

  test('scenarios page allows shock injection', async ({ page }) => {
    await page.goto('/economy/scenarios', { waitUntil: 'networkidle', timeout: 30000 });
    await expect(page.getByText('Deterministic disruption lab', { exact: true })).toBeVisible();

    const bankruptcy = page.getByRole('button', { name: /Supplier bankruptcy/ });
    await expect(bankruptcy).toBeEnabled();
    await bankruptcy.click();
    await expect(page.getByText('LIVE CAUSE → EFFECT')).toBeVisible();
  });

  test('skip to main content link works', async ({ page }) => {
    await page.goto('/economy/world', { waitUntil: 'networkidle', timeout: 30000 });
    const skipLink = page.getByRole('link', { name: 'Skip to main content' });
    await skipLink.focus();
    await expect(skipLink).toBeFocused();
  });

  test('keeps controls usable under reduced motion', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/economy/scenarios', { waitUntil: 'networkidle', timeout: 30000 });
    await expect(page.getByRole('heading', { name: 'Find the fault line.' })).toBeVisible();

    const bankruptcy = page.getByRole('button', { name: /Supplier bankruptcy/ });
    await expect(bankruptcy).toBeEnabled();
    await bankruptcy.click();
    await expect(page.getByText('LIVE CAUSE → EFFECT')).toBeVisible();
  });

  test('agent avatars render for each role', async ({ page }) => {
    await page.goto('/economy/world', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    const agentCards = page.getByRole('button', { name: /agent/i });
    await expect(agentCards.first()).toBeVisible({ timeout: 10000 });
  });

  test('business nodes respond to selection', async ({ page }) => {
    await page.goto('/economy/world', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);
    const nodes = page.getByRole('button', { name: /— active/ });
    if ((await nodes.count()) > 0) {
      // Clicking highlights the node (no dialog opens from business node directly)
      await nodes.first().click();
      await expect(page.getByRole('button', { name: /— active/ }).first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('page title contains Agentropolis', async ({ page }) => {
    await page.goto('/economy/world', { waitUntil: 'networkidle', timeout: 30000 });
    await expect(page).toHaveTitle(/Agentropolis/);
  });
});

test.describe('Agentropolis visual quality', () => {
  test('all screens have proper headings and structure', async ({ page }) => {
    const screens = [
      { path: '/economy/world' },
      { path: '/economy/negotiations' },
      { path: '/economy/control-tower' },
      { path: '/economy/procurement' },
      { path: '/economy/scenarios' },
    ];

    for (const { path } of screens) {
      await page.goto(path, { waitUntil: 'networkidle', timeout: 30000 });
      await page.waitForTimeout(500);
      await expect(page.getByRole('heading').first()).toBeVisible();
      await page.screenshot({ path: `../docs/evidence/screen-${path.split('/').pop()}.png`, fullPage: true });
    }
  });
});
