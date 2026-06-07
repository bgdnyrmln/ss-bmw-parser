#!/usr/bin/env python
# pylint: disable=unused-argument
import logging
import asyncio
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv, dotenv_values 
load_dotenv()

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


async def scan_loop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("scanning started, use /break to stop")
    sublink = ''

    while True:
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, requests.get, 'https://www.ss.lv/lv/transport/cars/bmw/')
            soup = BeautifulSoup(response.text, 'html.parser')
            listings = soup.find_all("td", class_="msg2")
            prices = soup.find_all("td", class_="msga2-o pp6")
            prices = str(prices).split('€')

            if sublink == listings[0].find('a', {'class': 'am'}).get('href'):
                pass
            else:
                listing = listings[0].find('a', {'class': 'am'})
                if listing is not None:
                    sublink = listing.get('href')
                    txt = str(listing.text)
                    txt = txt.split('. ')
                    price = str(prices[0])[::-1]
                    price = price.split('>""')
                    price = str(price[0])[::-1]
                    if price[0] == "<":
                        price = price.split('>')
                        price = str(price[1]).split('<')
                        price = str(price[0])
                    print(price + "€")
                    print(str(txt[0]) + "..." + "\n" + str("https://www.ss.lv" + sublink))
                    print("===")
                    response = await loop.run_in_executor(None, requests.get, 'https://www.ss.lv/' + sublink)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    pic = soup.find("img", class_="pic_thumbnail isfoto")
                    if pic is None:
                        pic_url = None  # or a placeholder image URL
                    else:
                        pic_url = pic.get("src")
                        if pic_url and pic_url.startswith("/"):
                            pic_url = "https://www.ss.lv" + pic_url
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=pic_url,
                        caption=str(txt[0]) + "...\n \n" + price + "€" + "\n \n" + "https://www.ss.lv" + sublink
                    )

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
    task = asyncio.create_task(scan_loop(update, context))
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
    application = Application.builder().token(os.getenv("TOKEN")).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("scan", scan))
    application.add_handler(CommandHandler("break", break_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
