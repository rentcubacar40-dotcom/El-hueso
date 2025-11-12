import os
import telebot

BOT_TOKEN = os.getenv("8175088122:AAGc9dNmgBf51FnuIoEDrNbJT9mcF8JKbFg")  # Tomará el token de las variables de entorno
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "Hola 👋 soy tu bot funcionando en Choreo!")

if __name__ == "__main__":
    bot.infinity_polling()
