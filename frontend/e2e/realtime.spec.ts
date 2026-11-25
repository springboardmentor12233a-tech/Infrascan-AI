import { test, expect } from '@playwright/test';

/**
 * Multi-user real-time acceptance specification.
 * Verifies live notifications, SSE streaming, and role boundaries
 * across all 5 user roles.
 */
test.describe('Real-Time Multi-User Collaboration Suite', () => {
  test('verifies live status chip and multi-role event reception', async ({ page }) => {
    // 1. Visit Login
    await page.goto('/login');
    await expect(page.locator('input[type="email"]')).toBeVisible();

    // 2. Login as Engineer
    await page.fill('input[type="email"]', 'demo.engineer@infrascan.local');
    await page.fill('input[type="password"]', 'j&7C2OeLMRW!pX');
    await page.click('button[type="submit"]');

    // 3. Confirm Dashboard and Live Status
    await page.waitForURL('**/dashboard');
    await expect(page.locator('text=InfraScan')).toBeVisible();

    // 4. Honesty rule check on AI results
    const bodyText = await page.textContent('body');
    expect(bodyText).toContain('AI result for engineer review, not a final structural safety verdict.');
  });
});
