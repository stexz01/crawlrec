import os, json, random, asyncio
from playwright.async_api import async_playwright
from .utils import random_chrome_ua, STEALTH_JS, log, YELLOW

class Extractor:
    def __init__(self, url, template, headful=False):
        self.file = template
        self.url = url
        self.headless = not headful
        
    async def run(self):
        if not os.path.exists(self.file):
            log("❌ JSON file not found.", color=YELLOW)
            return
        data = json.load(open(self.file))
        if not self.url: self.url = data.get("url")
        acts = data.get("actions", [])
        if not self.url or not acts:
            log(f"No actions/recorded found in {self.file}", color=YELLOW)
            return

        async with async_playwright() as p:
            ctx = await p.chromium.launch_persistent_context(
                headless=self.headless,                     # headful for more human
                slow_mo=random.randint(10,200),
                user_agent=random_chrome_ua(),
                viewport={"width": random.randint(1200, 1600), "height": random.randint(700, 1000)},
                locale="en-US",
                timezone_id=random.choice(["America/New_York","Europe/London","Asia/Kolkata"]),
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            await ctx.set_extra_http_headers({"accept-language":"en-US,en;q=0.9"})
            await ctx.add_init_script(STEALTH_JS)
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            
            try:
                await asyncio.wait_for(page.goto(self.url, wait_until="networkidle"), timeout=30)
            except Exception as TimeoutError:
                log(f"{self.url} not reachable (30sec timeout)")
                return

            for a in acts:
                try:
                    el = await page.query_selector(a["selector"]) or \
                         await page.query_selector(f"xpath={a['xpathSelector']}")
                    if not el:
                        print("❌ not found")
                        continue
                    if a["extract"] == "text":
                        val = await el.inner_text()
                    elif a["extract"] == "href":
                        val = await el.get_attribute("href")
                    elif a["extract"] == "value":
                        val = await el.input_value()
                    else:
                        val = await el.inner_text()
                    print(val)
                except Exception as e:
                    log(f"Extraction Error: {e}")
            await ctx.close()
            