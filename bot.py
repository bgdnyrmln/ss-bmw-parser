#!/usr/bin/env python
# pylint: disable=unused-argument
import logging
import asyncio
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Dict to track scanning tasks per user: {user_id: asyncio.Task}
scanning_tasks: dict[int, asyncio.Task] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}, use /scan to scan",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "/scan - start scanning BMW listings on ss.lv\n"
        "/break - stop scanning"
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.text == "67":
        await update.message.reply_text("stop")


async def scan_loop(update: Update) -> None:
    sublink = ""
    await update.message.reply_text("scanning started, use /break to stop")

    while True:
        try:
            url = "https://www.ss.lv/lv/transport/cars/bmw/"

            # Run blocking request in executor so it doesn't block the event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, requests.get, url)

            soup = BeautifulSoup(response.text, "html.parser")
            listings = soup.find_all("td", class_="msg2")
            prices = soup.find_all("td", class_="msga2-o pp6")
            prices = str(prices).split("€")

            if listings:
                listing = listings[0].find("a", {"class": "am"})
                if listing is not None:
                    current_link = listing.get("href")

                    if current_link != sublink:
                        sublink = current_link
                        txt = str(listing.text).split(". ")

                        price = str(prices[0])[::-1]
                        price = price.split('>""')
                        price = str(price[0])[::-1]
                        if price[0] == "<":
                            price = price.split('>')
                            price = str(price[1]).split('<')
                            price = str(price[0])
                        message = (
                            f"{txt[0]}...\n"
                            f"https://www.ss.lv{sublink}\n"
                            f"{price}€"
                        )
                        await update.message.reply_text(message)

            # asyncio.sleep is non-blocking and also serves as a cancellation point
            await asyncio.sleep(5)

        except asyncio.CancelledError:
            # Task was cancelled by /break — exit cleanly
            await update.message.reply_text("scanning stopped")
            return
        except Exception as e:
            logger.error(f"Error in scan loop: {e}")
            await asyncio.sleep(5)


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if user_id in scanning_tasks and not scanning_tasks[user_id].done():
        await update.message.reply_text("scan is already running")
        return

    # Create a new Task for this user — fully independent per user
    task = asyncio.create_task(scan_loop(update))
    scanning_tasks[user_id] = task


async def break_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    task = scanning_tasks.get(user_id)
    if task and not task.done():
        task.cancel()
        # Don't pop here — scan_loop will send the "stopped" message on CancelledError
    else:
        await update.message.reply_text("no active scan to stop")


def main() -> None:
    application = Application.builder().token("8929289008:AAHM8JyeM4mtWGFtre49fF4wKmDWZzbmkIk").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("scan", scan))
    application.add_handler(CommandHandler("break", break_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
