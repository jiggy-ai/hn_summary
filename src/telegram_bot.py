#
# send messages to telegram chat
#

import os
import telegram
import asyncio

TELEGRAM_API_TOKEN = os.environ["HNSUM_TELEGRAM_API_TOKEN"]

TELEGRAM_CHANNEL_ID = os.environ.get("HNSUM_TELGRAM_CHANNEL_ID", -1001685064201)


bot = telegram.Bot(TELEGRAM_API_TOKEN)


def send_message(text):
    """
    send telegram text to our group channel syncronously
    """
    async def send():
        chat = await bot.get_chat(TELEGRAM_CHANNEL_ID)
        # only send first 4096 bytes to avoid overruning telegram max message size
        await chat.send_message(text=text[:4096], parse_mode=telegram.ParseMode.MARKDOWN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(send())

