import os
import logging
import psutil
import platform
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

async def help_cmd(update: Update, context):
    await update.message.reply_text("Comandos:\n/start - Iniciar\n/help - Ayuda\n/status - Info del servidor")

async def echo(update: Update, context):
    text = update.message.text
    await update.message.reply_text(f"📝 Dijiste: {text}")

async def status(update: Update, context):
    try:
        # Información del sistema
        system_info = f"🖥️ **Sistema**: {platform.system()} {platform.release()}"
        
        # Uso de CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_info = f"⚡ **CPU**: {cpu_percent}%"
        
        # Memoria
        memory = psutil.virtual_memory()
        memory_info = f"💾 **Memoria**: {memory.percent}% ({memory.used//1024//1024}MB/{memory.total//1024//1024}MB)"
        
        # Disco
        disk = psutil.disk_usage('/')
        disk_info = f"💿 **Disco**: {disk.percent}% ({disk.used//1024//1024}MB/{disk.total//1024//1024}MB)"
        
        # Procesos
        processes_info = f"📊 **Procesos**: {len(psutil.pids())}"
        
        # Tiempo activo
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        uptime_info = f"⏰ **Uptime**: {str(uptime).split('.')[0]}"
        
        # Mensaje completo
        status_message = (
            "**📈 ESTADO DEL SERVIDOR**\n\n"
            f"{system_info}\n"
            f"{cpu_info}\n"
            f"{memory_info}\n"
            f"{disk_info}\n"
            f"{processes_info}\n"
            f"{uptime_info}\n\n"
            f"🕐 **Hora servidor**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        await update.message.reply_text(status_message)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error obteniendo status: {str(e)}")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    logger.info("Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
