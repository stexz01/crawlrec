import argparse, asyncio
from .recorder import Recorder
from .extractor import Extractor
from .utils import SmartFormatter, log, BOLD, YELLOW, RED, RESET

def main():
    parser = argparse.ArgumentParser(
        description="CrawlRec — Humanized Playwright Recorder & Extractor",
        formatter_class=SmartFormatter,
    )
    
    sub = parser.add_subparsers(dest="cmd", required=True)
    
    rec = sub.add_parser(
    "record",
    help="Record selectors interactively",
    description=f"Record selectors interactively.\nExample: {BOLD}{RED}crawlrec record https://example.com -o example.json{RESET}",
    )

    rec.add_argument("url", help="URL to record")
    rec.add_argument("-o", "--output", help="Custom output filename")

    ext = sub.add_parser(
        "extract",
        help="Extract data from saved JSON",
        description=f"Extract data from a saved CrawlRec JSON recording.\nExample: {BOLD}{RED}crawlrec extract crawls/example.json{RESET} -u https://example.com",
    )
    ext.add_argument("file", help="Path to JSON recording template")
    ext.add_argument("-u", "--url", help="URL to record")
    ext.add_argument("--headful", action="store_true", help="Run headful mode (headful for more human)")

    args = parser.parse_args()

    if args.cmd == "record":
        rec = Recorder(args.url, output=args.output)
        try:
            asyncio.run(rec.record())
        except KeyboardInterrupt:
            log("\nInterrupted. Saving & exiting safely.", color=YELLOW)
            try:
                asyncio.run(rec.safe_stop("cli.py"))
                pass
            except Exception:
                pass
        
    elif args.cmd == "extract":
        ext = Extractor(args.url, args.file, args.headful)
        try:
            results_ = asyncio.run(ext.run())
            if not results_:
                print("[]")
                return 
            else:
                for result in results_:
                    print(result)
                    
        except (KeyboardInterrupt, TypeError, ValueError) as e:
            parser.print_help()