import { expect, test } from '@playwright/test';

test('phone layouts keep navigation named and pages within the viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  for (const route of ['world', 'negotiations', 'control-tower', 'businesses', 'procurement', 'scenarios']) {
    await page.goto('/economy/' + route);
    await expect(page.getByRole('main')).toBeVisible();
    await expect(page.getByRole('link', { name: 'The World', exact: true })).toBeVisible();
    const width = await page.evaluate(() => ({ viewport: innerWidth, content: document.documentElement.scrollWidth }));
    expect(width.content, route).toBeLessThanOrEqual(width.viewport + 1);
  }
});
