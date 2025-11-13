import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context):
    user = update.effective_user
    await update.message.reply_text(f"🤖 Hola {user.first_name}! Bot activo en Choreo")

async def help_cmd(update: Update, context):
    await update.message.reply_text("Comandos:\n/start - Iniciar\n/help - Ayuda")

async def echo(update: Update, context):
    text = update.message.text
    await update.message.reply_text(f"📝 Dijiste: {text}")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    logger.info("Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
