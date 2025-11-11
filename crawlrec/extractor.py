import os, json, random, asyncio
from .utils import launch_browser, log, YELLOW, RED

class Extractor:
    def __init__(self, url, template, headful=False):
        self.file = template
        self.url = url
        self.headless = not headful
        self._error = False
        self._collected = []
        
    async def run(self):
        if not os.path.exists(self.file):
            log("❌ JSON file not found.", color=RED)
            return
        data = json.load(open(self.file))
        if not self.url: self.url = data.get("url")
        acts = data.get("actions", [])
        if not self.url or not acts:
            log(f"No actions/recorded found in {self.file}", color=YELLOW)
            return

        browser, ctx = await launch_browser(self.headless)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        
        await page.route("**/*", lambda route, req: 
        route.abort() if req.resource_type in ["image","media","font"] else route.continue_())

        try:
            # await page.goto(self.url, wait_until="networkidle") # stucks in never ending network api/ads calls....
            await asyncio.wait_for(page.goto(self.url, wait_until="domcontentloaded"), timeout=30) # soft networkidle: domcontentloaded + sleep
            await asyncio.sleep(random.randint(2,4))
            
        except TimeoutError:
            self._error = True
            log(f"This site can't be reached: {self.url}", color=RED)
        except:
            self._error = True
            log("(detected) site blocks automation aggressively. Use --headful")
            
        if self._error:
            await ctx.close(), await browser.close()
            return
        
        for a in acts:
            try:
                el = await page.query_selector(a["selector"]) or \
                        await page.query_selector(f"xpath={a['xpathSelector']}")
                if not el:
                    self._collected.append(None)
                    continue
                if a["extractType"] == "text":
                    val = await el.inner_text()
                elif a["extractType"] == "href":
                    val = await el.get_attribute("href")
                elif a["extractType"] == "value":
                    val = await el.input_value()
                else:
                    val = await el.inner_text()
                self._collected.append(val)
            except Exception as e:
                log(f"Extraction Error: {e}")
        await ctx.close(), await browser.close()
        return self._collected