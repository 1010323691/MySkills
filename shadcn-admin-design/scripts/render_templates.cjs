/* Render local template previews and check all five views at two widths.
   Requires Playwright. Set ADMIN_BROWSER_EXECUTABLE to an installed Chromium
   browser when the Playwright-managed browser is not installed. */
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

async function main() {
  const root = path.resolve(__dirname, '../assets/templates');
  const catalog = JSON.parse(fs.readFileSync(path.join(root, 'catalog.json'), 'utf8'));
  const output = path.join(root, 'previews');
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true,
    ...(process.env.ADMIN_BROWSER_EXECUTABLE ? { executablePath: process.env.ADMIN_BROWSER_EXECUTABLE } : {}) });
  const failures = [];
  const errors = [];
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 }, reducedMotion: 'reduce' });
  page.on('pageerror', error => errors.push(error.message));
  try {
    for (const template of catalog.templates) {
      const url = pathToFileURL(path.join(root, template.id, 'index.html')).href;
      for (const width of [1440, 390]) {
        await page.setViewportSize({ width, height: width === 390 ? 844 : 1050 });
        for (const view of ['overview', 'orders', 'charts', 'components', 'settings']) {
          await page.goto(`${url}#${view}`);
          await page.locator('#main h1').waitFor();
          const layout = await page.evaluate(() => ({
            width: innerWidth, scroll: document.documentElement.scrollWidth,
            charts: document.querySelectorAll('svg.chart').length,
            missingImages: Array.from(document.images).filter(i => !i.complete || i.naturalWidth === 0).length,
          }));
          if (layout.scroll > layout.width + 1) failures.push(`${template.id}/${view}/${width}: horizontal page overflow ${layout.scroll}`);
          if (view === 'charts' && layout.charts !== 3) failures.push(`${template.id}: chart view missing SVG charts`);
          if (view === 'overview') await page.screenshot({ path: path.join(output, `${template.id}${width === 390 ? '-mobile' : ''}.png`), fullPage: width === 390 });
          if (view === 'components' && width === 1440) await page.screenshot({ path: path.join(output, `${template.id}-components.png`), fullPage: true });
        }
      }
      console.log(`Rendered ${template.id}: five views at desktop + mobile widths`);
    }
    await page.setViewportSize({ width: 1440, height: 1050 });
    await page.goto(pathToFileURL(path.join(root, 'gallery.html')).href);
    await page.locator('.template-card').last().waitFor();
    await page.evaluate(async () => {
      const images = Array.from(document.images);
      images.forEach(image => image.loading = 'eager');
      await Promise.race([
        Promise.all(images.map(image => image.decode())),
        new Promise((_, reject) => setTimeout(() => reject(new Error('Gallery image decode timed out')), 15000)),
      ]);
    });
    await page.screenshot({ path: path.join(output, 'gallery.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    const galleryOverflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
    if (galleryOverflow) failures.push('Gallery: mobile horizontal overflow');
    if (errors.length) failures.push(...errors.map(message => `Browser error: ${message}`));
    if (failures.length) throw new Error(failures.join('\n'));
    console.log('PASS: all 60 template views, gallery images and responsive page bounds');
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
