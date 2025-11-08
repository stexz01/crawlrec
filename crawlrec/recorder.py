import asyncio, json, os, re, random, signal, re, importlib.resources
from pathlib import Path
from urllib.parse import urlparse
from InquirerPy import inquirer, get_style
from InquirerPy.base.control import Choice
from playwright.async_api import async_playwright
from .utils import random_chrome_ua, log, STEALTH_JS, YELLOW, CYAN, BOLD, RESET

STYLE = get_style({"question": "#00ffff bold", "pointer": "#9b5202 bold", "answer": "#d48022"})

# ------------------- RECORDER -------------------
class Recorder:
    def __init__(self, url, output=None, slow_mo=120):
        self.url = url
        self.output = output
        self.slow_mo = slow_mo
        
        self.actions, self.recording, self.ctx, self.shutdown_event  = [], True, None, asyncio.Event()

    def setup_signal_handlers(self, recorder: "Recorder"):
        """Attach SIGINT/SIGTERM handlers to trigger safe_stop()"""
        loop = asyncio.get_event_loop()

        def handle_sig(sig):
            asyncio.create_task(recorder.safe_stop(f"{sig.name} pressed."))

        try:
            loop.add_signal_handler(signal.SIGINT, lambda: handle_sig(signal.SIGINT))
            loop.add_signal_handler(signal.SIGTERM, lambda: handle_sig(signal.SIGTERM))
        except NotImplementedError:
            signal.signal(signal.SIGINT, lambda *_: asyncio.create_task(recorder.safe_stop("Ctrl+C pressed.")))
            signal.signal(signal.SIGTERM, lambda *_: asyncio.create_task(recorder.safe_stop("SIGTERM received.")))
        
    async def safe_stop(self, msg="🛑 Stopping..."):
        """Gracefully stop recorder, cancel all tasks, close browser, and exit cleanly."""
        if not self.recording:
            return
        
        try:
            self.recording = False
            self.shutdown_event.set()

            current, all_tasks = asyncio.current_task(), asyncio.all_tasks()

            for task in all_tasks:
                if task is current or task.done():
                    continue
                coro = getattr(task, "_coro", None)
                if coro and hasattr(coro, "__name__") and coro.__name__ in ("on_click", "idle_save_prompt"):
                    task.cancel()

            others = [t for t in asyncio.all_tasks() if not t.done() and t is not asyncio.current_task()]
            for t in others:
                try:
                    t.cancel()
                except Exception:
                    pass
                
            try:
                if self.ctx:
                    await asyncio.wait_for(self.ctx.close(), timeout=0.5)
            except Exception as e:
                if "Target page" not in str(e):
                    pass
                    
            try:
                await self._save()
            except Exception as e:
                log(f"⚠️ Error saving: {e}", color=YELLOW)
                
        except:
            pass

        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            for t in pending:
                t.cancel()
            try:
                await asyncio.gather(*pending, return_exceptions=True)
            except Exception:
                pass

        os._exit(0)

    async def idle_save_prompt(self):
        """Handle click events from injected JS"""
        if not self.recording:
            return
        
        choices = [Choice(value="exit", name=f"Save & Exit?")]
        
        try:
            ans = await inquirer.select(
                    message="↓",
                    choices=choices,
                    qmark="",
                    pointer=">",
                    style=STYLE,
                    default=0
                ).execute_async()
        except (KeyboardInterrupt, asyncio.CancelledError):
            await self.safe_stop("Interrupted by user.")
            return
        except asyncio.TimeoutError:
            os.system('cls' if os.name == 'nt' else 'clear')
            pass
            return

        if "exit" in ans:
            await self.safe_stop("Exit & save triggered.")
            return

    async def on_click(self, data):
        """Handle click events from injected JS"""
        if not self.recording:
            return

        choices = []
        
        text = data.get("text")
        href = data.get("href")
        
        if text or href:
        
            if text: choices.append(Choice(value="text", name=f"{text}"))
            if href: choices.append(Choice(value="href", name=f"{href}"))
            choices += ["exit & save"]
            
            try:
                ans = await inquirer.select(
                        message="↓",
                        choices=choices,
                        # qmark="↓",
                        qmark="",
                        pointer=">",
                        style=STYLE,
                        default=0
                    ).execute_async()
            except (KeyboardInterrupt, asyncio.CancelledError):
                await self.safe_stop("Interrupted by user.")
                return
            except asyncio.TimeoutError:
                os.system('cls' if os.name == 'nt' else 'clear')
                await self.idle_save_prompt()
                return

            if "exit" in ans:
                await self.safe_stop("Exit & Save.")
                return

            self.actions.append({
                "selector": data.get("selector"),
                "xpathSelector": data.get("xpathSelector"),
                "extract": ans,
                "text": text,
                "href": href,
                "value": data.get("value"),
            })
            
            if ans == "text": print(f"{BOLD}{YELLOW}→ Saved {RESET}{BOLD}{CYAN}({text}){RESET}")
            if ans == "href": print(f"{BOLD}{YELLOW}→ Saved {RESET}{BOLD}{CYAN}({href}){RESET}")
            
        await self.idle_save_prompt()

    def _make_output_path(self):
        if self.output:
            custom_path = Path(self.output).expanduser().resolve()
            custom_path.parent.mkdir(parents=True, exist_ok=True)
            return str(custom_path)

        base_dir = Path.cwd() / "crawls"  # saves to ./crawls by default
        base_dir.mkdir(parents=True, exist_ok=True)

        domain = re.sub(r"^www\.", "", urlparse(self.url).netloc)
        base_name = base_dir / f"{domain}.json"

        count = 2
        final_path = base_name
        while final_path.exists():
            final_path = base_dir / f"{domain}{count}.json"
            count += 1

        return str(final_path)

    async def _save(self):
        """Write actions to JSON"""
        if not self.actions:
            log("No elements recorded.", color=YELLOW)
            return
        path = self._make_output_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"url": self.url, "actions": self.actions}, f, indent=2)
        print(f"{BOLD}{YELLOW}→ Saved {len(self.actions)} actions → {path}{RESET}")

    async def record(self):
        """Main recorder loop"""
        try:
            async with async_playwright() as p:
                ctx = await p.chromium.launch_persistent_context(
                    user_data_dir="/tmp/crawlrec_extract",
                    headless=False,                     
                    slow_mo=random.randint(10,200),
                    user_agent=random_chrome_ua(),
                    viewport={"width": random.randint(1200, 1600), "height": random.randint(700, 1000)},
                    locale="en-US",
                    timezone_id=random.choice(["America/New_York","Europe/London","Asia/Kolkata"]),
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                )
                await ctx.set_extra_http_headers({"accept-language":"en-US,en;q=0.9"})
                await ctx.add_init_script(STEALTH_JS)
                
                self.setup_signal_handlers(self)

                page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                await ctx.expose_binding("recordClick",
                    lambda src, data: asyncio.create_task(self.on_click(data)))

                try:
                    with importlib.resources.files("crawlrec").joinpath("rec.js").open("r", encoding="utf-8") as f:
                        rec_js = f.read()
                except FileNotFoundError:
                    log("❌ rec.js missing in package.", YELLOW); 
                    await self.safe_stop()
                    return

                # await page.goto(self.url, wait_until="domcontentloaded")
                try:
                    await asyncio.wait_for(page.goto(self.url, wait_until="networkidle"), timeout=30)
                except Exception as TimeoutError:
                    log(f"{self.url} not reachable (30sec timeout)")
                    return
                
                await page.evaluate(rec_js)
                
                log(f"Starting recorder for: {BOLD}{self.url}{RESET}", icon="", color=YELLOW)
                log("Human-mode active (stealth JS, random UA, mouse jitter enabled).", icon="", color=YELLOW)
                log("Click Text/Links to record.", icon="", color=YELLOW)

                try:
                    while self.recording and not self.shutdown_event.is_set():
                        await asyncio.sleep(0.3)
                except (KeyboardInterrupt, asyncio.CancelledError):
                    await self.safe_stop("🧹 Keyboard interrupt.")
                    pass
                except Exception as e:
                    log(f"Record Error occurred: {e}")
                    await self.safe_stop("Record Error occurred.")
                finally:
                    await self.safe_stop()
                    
        except asyncio.CancelledError:
            pass
        