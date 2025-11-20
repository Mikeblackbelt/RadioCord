import aiosqlite
import asyncio

async def messageDownloadRate(time: int):
    # Use aiosqlite for non-blocking database operations
    async with aiosqlite.connect('messages.db') as conn:
        cursor = await conn.cursor()
        
        # First count
        await cursor.execute("SELECT COUNT(*) FROM messages;")
        pages_before = (await cursor.fetchone())[0]

        # Non-blocking sleep allows other async tasks to run
        await asyncio.sleep(time)

        # Second count
        await cursor.execute("SELECT COUNT(*) FROM messages;")
        pages_after = (await cursor.fetchone())[0]

    # The connection is closed automatically by the 'async with' block

    # Ensure time is not zero to prevent ZeroDivisionError
    if time == 0:
        return 0 
        
    return (pages_after - pages_before) / time #msg per second

if __name__ == "__main__":
    import asyncio
    rate = asyncio.run(messageDownloadRate(10))
    print(f"Message download rate: {rate} messages/second")