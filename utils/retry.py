import asyncio
import random

async def retry_async(fn, retries=3, base_delay=1, factor=2, jitter=0.3):
    last_error = None

    for attempt in range(retries):
        try:
            return await fn()
        except Exception as e:
            last_error = e
            if attempt == retries - 1:
                raise
            delay = base_delay * (factor ** attempt)
            delay = delay * (1 + random.uniform(-jitter, jitter))
            await asyncio.sleep(delay)

    raise last_error