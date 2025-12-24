import os
import telebot
import tempfile
import mimetypes
from pathlib import Path
from datetime import datetime
import json
import shutil
from collections import defaultdict

# Configuración
API_TOKEN = '8559990136:AAGEKdwIqiUVOr3h5eqK5eRNR4PGup0Veg8'  # Reemplaza con tu token de bot
bot = telebot.TeleBot(API_TOKEN)

# Almacenamiento en memoria (para producción usa Redis o base de datos)
USER_THUMBNAILS = {}  # {user_id: thumbnail_path}
USER_FILES = {}  # {user_id: [file_paths]}

# Directorio temporal
TEMP_DIR = tempfile.mkdtemp(prefix='telegram_bot_')

def format_size(size_bytes):
    """Formatea el tamaño en bytes a texto legible"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def get_file_icon(extension):
    """Devuelve un emoji según la extensión del archivo"""
    icon_map = {
        '.txt': '📄', '.pdf': '📕', '.doc': '📘', '.docx': '📘',
        '.apk': '📱', '.exe': '⚙️', '.zip': '🗜️', '.rar': '🗜️',
        '.7z': '🗜️', '.mp3': '🎵', '.mp4': '🎬', '.jpg': '🖼️',
        '.png': '🖼️', '.gif': '🖼️', '.iso': '💿', '.py': '🐍',
        '.js': '📜', '.html': '🌐', '.css': '🎨', '.json': '📊',
    }
    return icon_map.get(extension.lower(), '📁')

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = """
🤖 **Bot de Archivos con Thumbnail**

**Cómo funciona:**
1. Envía una **foto** para establecerla como thumbnail para todos tus archivos
2. Luego envía **cualquier archivo** (txt, apk, zip, etc.)
3. Recibirás el archivo de vuelta con la foto como portada

**Comandos:**
/setthumb - Cambiar tu foto de portada
/clearthumb - Eliminar tu foto de portada
/mythumb - Ver tu foto actual
/help - Mostrar esta ayuda

**Ejemplo en la imagen:**
- Se envió una foto del juego
- Luego se enviaron archivos .txt
- Cada archivo muestra esa foto como portada
"""
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['setthumb'])
def set_thumbnail_command(message):
    bot.send_message(message.chat.id, 
                    "📸 Envíame una foto para usar como portada para todos tus archivos. "
                    "Esta foto se mostrará como thumbnail cada vez que envíes un archivo.")

@bot.message_handler(commands=['clearthumb'])
def clear_thumbnail_command(message):
    user_id = message.chat.id
    if user_id in USER_THUMBNAILS:
        # Eliminar archivo físico si existe
        if os.path.exists(USER_THUMBNAILS[user_id]):
            try:
                os.remove(USER_THUMBNAILS[user_id])
            except:
                pass
        del USER_THUMBNAILS[user_id]
        bot.send_message(message.chat.id, "🗑️ Thumbnail eliminado. Envía una nueva foto con /setthumb")
    else:
        bot.send_message(message.chat.id, "ℹ️ No tienes un thumbnail configurado. Envía una foto con /setthumb")

@bot.message_handler(commands=['mythumb'])
def show_thumbnail_command(message):
    user_id = message.chat.id
    if user_id in USER_THUMBNAILS and os.path.exists(USER_THUMBNAILS[user_id]):
        with open(USER_THUMBNAILS[user_id], 'rb') as photo:
            bot.send_photo(message.chat.id, photo, 
                          caption="📸 Esta es tu foto de portada actual. Se usará para todos los archivos que envíes.")
    else:
        bot.send_message(message.chat.id, 
                        "ℹ️ No tienes una foto de portada configurada.\n\n"
                        "Envía cualquier foto y se usará automáticamente, o usa /setthumb para establecer una.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """Maneja fotos enviadas - se convierten en thumbnail automáticamente"""
    user_id = message.chat.id
    
    try:
        # Obtener la foto de mejor calidad (última en la lista)
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_photo = bot.download_file(file_info.file_path)
        
        # Guardar como thumbnail del usuario
        thumb_path = os.path.join(TEMP_DIR, f"thumbnail_{user_id}.jpg")
        with open(thumb_path, 'wb') as f:
            f.write(downloaded_photo)
        
        # Guardar en memoria
        USER_THUMBNAILS[user_id] = thumb_path
        
        # Confirmar al usuario
        bot.reply_to(message, 
                    "✅ Foto establecida como portada para todos tus archivos.\n\n"
                    "Ahora envía cualquier archivo y aparecerá con esta imagen como thumbnail.")
        
        # Opcional: mostrar vista previa
        with open(thumb_path, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, 
                          caption="📸 Vista previa de tu thumbnail")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error al guardar la foto: {str(e)}")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    """Maneja cualquier archivo enviado como documento"""
    user_id = message.chat.id
    
    try:
        # Verificar si el usuario tiene thumbnail
        user_has_thumbnail = user_id in USER_THUMBNAILS and os.path.exists(USER_THUMBNAILS[user_id])
        
        if not user_has_thumbnail:
            # Si no tiene thumbnail, pedirle que envíe una foto primero
            bot.reply_to(message,
                        "📸 Primero necesitas enviar una foto para usar como portada.\n\n"
                        "Envía cualquier foto y luego vuelve a enviar este archivo.")
            return
        
        # Obtener información del archivo
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name or f"archivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        file_size = message.document.file_size or 0
        
        # Descargar el archivo
        bot.send_chat_action(message.chat.id, 'upload_document')
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Guardar temporalmente
        temp_file_path = os.path.join(TEMP_DIR, file_name)
        with open(temp_file_path, 'wb') as f:
            f.write(downloaded_file)
        
        # Obtener extensión para el icono
        file_ext = Path(file_name).suffix
        file_icon = get_file_icon(file_ext)
        
        # Preparar el caption (como en la imagen)
        file_size_str = format_size(file_size)
        caption = f"{file_icon} {file_name}\n📏 {file_size_str}"
        
        # Enviar el archivo con el thumbnail del usuario
        with open(USER_THUMBNAILS[user_id], 'rb') as thumb, \
             open(temp_file_path, 'rb') as file_data:
            
            # Enviar como documento con thumbnail personalizado
            bot.send_document(
                chat_id=message.chat.id,
                document=file_data,
                caption=caption,
                parse_mode=None,  # Sin formato para que se vea como texto plano
                visible_file_name=file_name,  # Nombre que se mostrará
                thumbnail=thumb  # Thumbnail personalizado
            )
        
        # Limpiar archivo temporal
        try:
            os.remove(temp_file_path)
        except:
            pass
        
        # Confirmación
        bot.send_message(message.chat.id, 
                        f"✅ Archivo enviado con tu thumbnail personalizado.\n"
                        f"📁 {file_name}\n"
                        f"📊 {file_size_str}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error al procesar el archivo: {str(e)}")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Maneja mensajes de texto"""
    if message.text.startswith('/'):
        return
    
    # Si envía texto normal, recordarle cómo funciona
    bot.reply_to(message,
                "📁 Para usar el bot:\n"
                "1. Envía una **foto** (se usará como portada)\n"
                "2. Luego envía **archivos** (txt, apk, zip, etc.)\n"
                "3. Cada archivo mostrará tu foto como thumbnail\n\n"
                "Usa /help para más información.")

if __name__ == '__main__':
    print("🤖 Bot de Archivos con Thumbnail Automático Iniciado")
    print("📸 Envía una foto primero, luego cualquier archivo")
    print(f"📁 Directorio temporal: {TEMP_DIR}")
    
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Limpieza final
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR, ignore_errors=True)
