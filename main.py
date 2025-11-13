import os
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context):
    user = update.effective_user
    await update.message.reply_text(f"🤖 Hola {user.first_name}! Bot activo en Choreo")

async def status(update: Update, context):
    try:
        # Información básica que SÍ funciona en Choreo
        status_message = (
            "**📈 ESTADO DEL BOT**\n\n"
            f"✅ **Bot**: Activo y funcionando\n"
            f"🕐 **Hora servidor**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🌐 **Hosting**: Choreo\n"
            f"📊 **Estado**: Online\n\n"
            "✨ Todos los sistemas operativos correctamente"
        )
        
        await update.message.reply_text(status_message)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def echo(update: Update, context):
    text = update.message.text
    await update.message.reply_text(f"📝 Dijiste: {text}")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    logger.info("Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
