import config
import logging
from pymongo import MongoClient
from requests import post
import subprocess
from telegram import Update, constants
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    Defaults
)
from telegram.helpers import escape_markdown
import traceback


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filemode="w",
    filename="logs/log.txt"
)

if config.db_uri:
    client = MongoClient(config.db_uri, serverSelectionTimeoutMS=5000)
else:
    client = MongoClient(
        config.db_ip,
        username=config.db_user,
        password=config.db_pass,
        authSource=config.db_auth
    )
database = client["website"]


with open("./build-timestamp", "r") as f:
    build_date = f.readline()

commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()


def check_permms(update):
    if not update.effective_user.username == config.username:
        logging.warn(f"{update.effective_user.id} tried to use the bot")
        return False

    return True


def parse_poke(poke: str):
    try:
        return database["pokedex"].find_one({"id": int(poke)})["name"]
    
    except Exception as e:
        logging.info(f"Assuming {poke} is an int went wrong, has to be a name")
        return poke.lower()


async def version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"Container built on `{build_date}`\nWith commit [{commit}]({config.gh_link})"
    await update.message.reply_text(text=text.replace("-", r"\-"), quote=False) 


def update_region_html(name):
    _filter = {name: {"$exists": True}}
    text = ""
    for region in database["40dex"].find_one(_filter)["regions"]:
        url   = f"{config.scheme}://{config.domain}/40dex/re-gen/{region}"
        res = post(
            url,
            json={"password": config.rm_pass}
        )
        text += f"Query to: {url} got response: {res.text}\n"
    return escape_markdown(text, version=2)


async def update_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_permms(update):
        return -1 #Will also end ConvHand

    poke = context.args[0]
    name = parse_poke(poke)

    try:
        _filter = {name: {"$exists": True}}
        operation = {"$inc": {name: 1 if update.message.text.split(" ")[0] in ["/catch"] else -1}}

        table = database["trade-dex"]

        table.update_one(
            _filter,
            operation
        )
        
        counter = table.find_one(_filter)[name]

        text = f"Updated\.\n`{name}`'s trade counter is now: **{counter}**"
        await update.message.reply_text(text=text.replace("-", r"\-"), quote=False)

        text = update_region_html(name)
        await update.message.reply_text(text=f"HTML regenerated:\n{text}", quote=False)

    # If something goes wrong, let's inform instead of silently failing
    except Exception as e:
        logging.error(f"Updating {name}'s trade-dex failed due to: {traceback.format_exc()}")
        text = f"Updating `{name}`'s trade counter failed\.\nCheck the log for further details"
        await update.message.reply_text(text=text.replace("-", r"\-"), quote=False)



async def update_40(update: Update, context: ContextTypes.DEFAULT_TYPE):    
    if not check_permms(update):
        return -1 #Will also end ConvHand

    poke = context.args[0]
    name = parse_poke(poke)

    try:
        _filter = {name: {"$exists": True}}
        operation = {"$inc": {name: 1 if update.message.text.split(" ")[0] in ["/add", "/inc"] else -1}}

        table = database["40dex"]

        table.update_one(
            _filter,
            operation
        )
        
        counter = table.find_one(_filter)[name]

        text = f"Updated\.\n`{name}`'s 40dex counter is now: **{counter}**"
        await update.message.reply_text(text=text.replace("-", r"\-"), quote=False)
        
        text = update_region_html(name)
        await update.message.reply_text(text=f"HTML regenerated:\n{text}", quote=False)

    # If something goes wrong, let's inform instead of silently failing
    except Exception as e:
        logging.error(f"Updating {name}'s 40dex failed due to: {traceback.format_exc()}")
        text = f"Updating `{name}`'s 40dex counter failed\.\nCheck the log for further details"
        await update.message.reply_text(text=text.replace("-", r"\-"), quote=False)


if __name__ == "__main__":
    application = (
        ApplicationBuilder()
        .token(config.token)
        .defaults(Defaults(
            parse_mode=constants.ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True
        ))
        .build()
    )

    #========
    # Version
    application.add_handler(CommandHandler("version", version))

    #======
    # 40dex
    application.add_handler(CommandHandler("add", update_40))
    application.add_handler(CommandHandler("inc", update_40))    
    application.add_handler(CommandHandler("sub", update_40))
    application.add_handler(CommandHandler("dec", update_40))

    #==========
    # Trade-dex
    application.add_handler(CommandHandler("catch", update_trade))
    application.add_handler(CommandHandler("trade", update_trade))

    application.run_polling()
