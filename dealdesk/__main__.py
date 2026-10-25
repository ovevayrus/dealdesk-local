"""Command line: start the demo server, run a tool, or drop the supplier feed for the watcher.

    python -m dealdesk                                   # start http://127.0.0.1:8000
    python -m dealdesk tool price_deal '{"offer_revenue": "136000.00"}'
    python -m dealdesk drop-supplier-feed                # copy synthetic-costs-v2 into the watched folder
    python -m dealdesk reset                             # restore the initial feed, quote context, and chat
"""

import argparse
import json
import shutil
import sys

from .config import get_settings
from .costs import FEEDS_DIR, SHOCK_FEED_VERSION


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m dealdesk", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", nargs="?", default="serve",
                        choices=["serve", "tool", "drop-supplier-feed", "reset"])
    parser.add_argument("tool_name", nargs="?", help="with 'tool': search_documents, price_deal, "
                        "forecast_costs, or apply_demo_cost_update")
    parser.add_argument("arguments", nargs="?", default="{}", help="with 'tool': JSON object of arguments")
    args = parser.parse_args()
    settings = get_settings()

    if args.command == "tool":
        from .state import Store
        from .tools import DemoTools, run_tool

        store = Store(settings.db_path)
        try:
            output = run_tool(DemoTools(settings, store), store, args.tool_name or "",
                              json.loads(args.arguments), "cli-agent")
        except (KeyError, TypeError, ValueError) as exc:
            print(json.dumps({"error": str(exc)}))
            sys.exit(2)
        print(json.dumps(output, indent=1))
    elif args.command == "serve":
        from .app import main as serve

        serve()
    elif args.command == "drop-supplier-feed":
        settings.incoming_feed_dir.mkdir(parents=True, exist_ok=True)
        target = settings.incoming_feed_dir / f"{SHOCK_FEED_VERSION}.json"
        shutil.copyfile(FEEDS_DIR / f"{SHOCK_FEED_VERSION}.json", target)
        print(f"Copied {SHOCK_FEED_VERSION} to {target}; the running server's watcher will pick it up "
              f"within {settings.watch_interval_seconds:g} seconds.")
    else:
        from .state import Store
        from .tools import DemoTools

        DemoTools(settings, Store(settings.db_path)).reset()
        print("Demo state reset: initial feed, no quote versions, no review events, empty chat.")


if __name__ == "__main__":
    main()
