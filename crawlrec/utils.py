import argparse, random
from datetime import datetime

# ANSI colors
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"


CHROME_BASES = [
    ("Windows NT 10.0; Win64; x64", "Chrome"),
    ("Macintosh; Intel Mac OS X 10_15_7", "Safari"),
    ("X11; Linux x86_64", "Chrome"),
]

"""
2025	
Current Stable Chrome	
Good Range
131, 135  (OR) 128, 136
"""

CHROME_MAJOR_MIN = (128, 136)
CHROME_BUILD_MIN = 1000
CHROME_BUILD_MAX = 9999

def random_chrome_ua():
    platform, family = random.choice(CHROME_BASES)
    major = random.randint(*CHROME_MAJOR_MIN)
    build = random.randint(CHROME_BUILD_MIN, CHROME_BUILD_MAX)
    build2 = random.randint(0,99)
    if family == "Chrome":
        return (f"Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{major}.0.{build}.{build2} Safari/537.36")
    else:
        version = f"{random.randint(13,18)}.0.{random.randint(1,9)}"
        return (f"Mozilla/5.0 ({platform}) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                f"Version/{version} Safari/605.1.15")
        
# for multiple parallel crawlers, assign a different UA to each worker. (future additional)
def ua_pool(n=8):
    base = [random_chrome_ua() for _ in range(n)]
    base += [
        # Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        # Android Chrome
        "Mozilla/5.0 (Linux; Android 12; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.6167.85 Mobile Safari/537.36",
    ]
    return base


STEALTH_JS = r"""
(() => {
  try {
    // navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

    // chrome.runtime
    if (!window.chrome) window.chrome = { runtime: {} };

    // languages
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });

    // plugins (fake small plugin list)
    Object.defineProperty(navigator, 'plugins', {
      get: () => [{ name: 'Chrome PDF Plugin' }, { name: 'Widevine' }]
    });

    // mimeTypes
    Object.defineProperty(navigator, 'mimeTypes', {
      get: () => [{ type: 'application/pdf', description: '', suffixes: 'pdf' }]
    });

    // hardwareConcurrency / deviceMemory
    try {
      Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 4 });
      Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
    } catch(e){}

    // platform + vendor
    try {
      Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
      Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });
    } catch(e){}

    // userAgentData (for modern detection)
    try {
      // minimal userAgentData
      if (!navigator.userAgentData) {
        navigator.userAgentData = {
          brands: [{ brand: "Chromium", version: "122" }, { brand: "Google Chrome", version: "122" }],
          mobile: false,
          getHighEntropyValues: (hints) => Promise.resolve({platform: 'Windows'})
        };
      }
    } catch(e){}

    // permissions.query patch (notifications)
    try {
      const origQuery = navigator.permissions.query;
      navigator.permissions.query = (params) => {
        if (params && params.name === 'notifications') {
          return Promise.resolve({ state: Notification.permission });
        }
        return origQuery.call(navigator.permissions, params);
      }
    } catch(e){}

    // WebGL vendor/renderer spoof
    try {
      const getParameter = WebGLRenderingContext.prototype.getParameter;
      WebGLRenderingContext.prototype.getParameter = function(parameter) {
        // UNMASKED_VENDOR_WEBGL = 37445, UNMASKED_RENDERER_WEBGL = 37446
        if (parameter === 37445) return "Intel Inc.";
        if (parameter === 37446) return "Intel(R) Iris(TM) Graphics";
        return getParameter.call(this, parameter);
      };
    } catch(e){}

    // mediaDevices.enumerateDevices
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        const origEnum = navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
        navigator.mediaDevices.enumerateDevices = () => origEnum().catch(_=>[]);
      }
    } catch(e){}

    // toString hygiene for functions
    try {
      const oldToString = Function.prototype.toString;
      const re = /native code/;
      Function.prototype.toString = function() {
        if (this === Object.prototype.toString) return 'function toString() { [native code] }';
        return oldToString.call(this);
      };
    } catch(e){}

    // small random timing jitter for performance.now (avoid exact 0)
    try {
      const realNow = performance.now.bind(performance);
      performance.now = function() { return realNow() + Math.random() * 5; };
    } catch(e){}

    // maxTouchPoints
    try { Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 }); } catch(e){}

  } catch(e) {
    // don't break page if stealth fails
    console.warn('stealth init failed', e);
  }
})();
"""

def log(msg, icon="", color=RED, end="\n"):
    """Unified styled console logger."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{BOLD}{color}[{timestamp}] {icon} {msg}{RESET}", end=end)

class SmartFormatter(argparse.HelpFormatter):
    """Better argparse formatter for subcommands."""
    def _format_action(self, action):
        parts = super()._format_action(action)
        if isinstance(action, argparse._SubParsersAction):
            for sub in action.choices.values():
                parts += f"\n    {sub.prog.split()[-1]}  {sub.description or ''}\n"
        return parts