import asyncio
import logging
from ict_scanner.orchestrator.scheduler import Scheduler
from ict_scanner.db.database import init_db
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(message)s")

async def main() -> None:
    print("Initializing Database...")
    await init_db()
    
    print("Starting Manual Scan Cycle...")
    scheduler = Scheduler()
    
    # We will hook into the process_pair to print the status.
    original_process_pair = scheduler.process_pair
    
    async def process_pair_wrapper(pair: Any) -> None:
        print(f"Scanning {pair.symbol}...")
        await original_process_pair(pair)
        print(f"[{pair.symbol}] Scan complete.")
        
    scheduler.process_pair = process_pair_wrapper
    
    await scheduler.run_once()
    
    print("-" * 40)
    print("Manual Scan Completed.")

if __name__ == "__main__":
    asyncio.run(main())
