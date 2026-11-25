// Render tools/banner.html to the banner of the store page.
//
//     NODE_PATH=$(npm root -g) node tools/make_banner.js
//
// Playwright only drives the browser: CHROME names the Chromium binary
// when the one Playwright caches is not the one to use. The picture is 1200 x 600: the cover frame at the top of
// the store page is 2:1 and crops any other ratio.

const path = require('path');
const {chromium} = require('playwright');

const OUT = path.join(__dirname, '..', 'pos_nm_currency_exchange', 'static', 'description', 'banner.png');

(async () => {
    const browser = await chromium.launch(
        process.env.CHROME ? {executablePath: process.env.CHROME} : {});
    const page = await browser.newPage({viewport: {width: 1200, height: 600}, deviceScaleFactor: 1});
    await page.goto('file://' + path.join(__dirname, 'banner.html'));
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({path: OUT, clip: {x: 0, y: 0, width: 1200, height: 600}});
    await browser.close();
    console.log('banner: ' + OUT);
})();
