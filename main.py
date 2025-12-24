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
API_TOKEN = os.environ.get('API_TOKEN') or '8137417206:AAEiWlYonvi1WJajQbxF_19xQVI9iLDgh9I'
bot = telebot.TeleBot(API_TOKEN)

# Límite de tamaño: 50 MB en bytes
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Almacenamiento en memoria
USER_THUMBNAILS = {}  # {user_id: thumbnail_path}
USER_STATES = defaultdict(dict)  # {user_id: {'state': '', 'data': {}}}
USER_PENDING_FILES = {}  # {user_id: file_data}

# Estados del usuario
class UserState:
    WAITING_FILE = 'waiting_file'
    WAITING_THUMBNAIL = 'waiting_thumbnail'
    WAITING_RENAME = 'waiting_rename'

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
🤖 **Bot de Archivos con Thumbnail y Renombrado**

**📏 Límite de tamaño:** 50 MB por archivo

**📋 Cómo funciona:**
1. Envía una **foto** para establecerla como thumbnail (opcional)
2. Envía cualquier **archivo** (hasta 50 MB)
3. Elige si quieres **renombrarlo** o enviarlo como está
4. Recibe el archivo con tu thumbnail personalizado

**🔄 Flujo completo:**
Foto → Archivo → [Renombrar?] → Enviar con Thumbnail

**⚡ Comandos rápidos:**
/setthumb - Establecer o cambiar tu thumbnail
/clearthumb - Eliminar tu thumbnail actual
/mythumb - Ver tu thumbnail actual
/rename - Activar modo renombrado para el próximo archivo
/cancel - Cancelar operación actual
/help - Mostrar esta ayuda
"""
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')
    USER_STATES[message.chat.id] = {'state': UserState.WAITING_FILE}

@bot.message_handler(commands=['setthumb'])
def set_thumbnail_command(message):
    USER_STATES[message.chat.id] = {'state': UserState.WAITING_THUMBNAIL}
    bot.send_message(message.chat.id, 
                    "📸 Envíame una foto para usar como portada para todos tus archivos.")

@bot.message_handler(commands=['clearthumb'])
def clear_thumbnail_command(message):
    user_id = message.chat.id
    if user_id in USER_THUMBNAILS:
        if os.path.exists(USER_THUMBNAILS[user_id]):
            try:
                os.remove(USER_THUMBNAILS[user_id])
            except:
                pass
        del USER_THUMBNAILS[user_id]
        bot.send_message(message.chat.id, "🗑️ Thumbnail eliminado.")
    else:
        bot.send_message(message.chat.id, "ℹ️ No tienes un thumbnail configurado.")

@bot.message_handler(commands=['mythumb'])
def show_thumbnail_command(message):
    user_id = message.chat.id
    if user_id in USER_THUMBNAILS and os.path.exists(USER_THUMBNAILS[user_id]):
        with open(USER_THUMBNAILS[user_id], 'rb') as photo:
            bot.send_photo(message.chat.id, photo, 
                          caption="📸 Tu thumbnail actual")
    else:
        bot.send_message(message.chat.id, "ℹ️ No tienes thumbnail. Envía una foto.")

@bot.message_handler(commands=['rename'])
def rename_command(message):
    USER_STATES[message.chat.id] = {'state': UserState.WAITING_RENAME}
    bot.send_message(message.chat.id, 
                    "✏️ **Modo renombrado activado**\n\n"
                    "El próximo archivo que envíes te pedirá un nuevo nombre.\n"
                    "Usa /cancel para desactivar este modo.", 
                    parse_mode='Markdown')

@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    user_id = message.chat.id
    USER_STATES[user_id] = {'state': UserState.WAITING_FILE}
    
    # Limpiar archivos pendientes
    if user_id in USER_PENDING_FILES:
        file_path = USER_PENDING_FILES[user_id].get('temp_path')
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        del USER_PENDING_FILES[user_id]
    
    bot.send_message(message.chat.id, "❌ Operación cancelada.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """Maneja fotos enviadas como thumbnails"""
    user_id = message.chat.id
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_photo = bot.download_file(file_info.file_path)
        
        thumb_path = os.path.join(TEMP_DIR, f"thumbnail_{user_id}.jpg")
        with open(thumb_path, 'wb') as f:
            f.write(downloaded_photo)
        
        USER_THUMBNAILS[user_id] = thumb_path
        USER_STATES[user_id] = {'state': UserState.WAITING_FILE}
        
        bot.reply_to(message, 
                    "✅ **Thumbnail establecido**\n\n"
                    "Ahora envía un archivo (hasta 50 MB).\n"
                    "Usa /rename antes de enviar si quieres cambiarlo de nombre.",
                    parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    """Maneja archivos enviados como documentos"""
    user_id = message.chat.id
    
    # Verificar tamaño del archivo (50 MB límite)
    if message.document.file_size and message.document.file_size > MAX_FILE_SIZE:
        size_mb = message.document.file_size / (1024 * 1024)
        bot.reply_to(message, 
                    f"❌ **Archivo demasiado grande**\n\n"
                    f"Tamaño: {size_mb:.1f} MB\n"
                    f"Límite: 50 MB\n\n"
                    f"Por favor, envía un archivo más pequeño.",
                    parse_mode='Markdown')
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        original_name = message.document.file_name or f"archivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        file_size = message.document.file_size or 0
        
        # Descargar archivo
        bot.send_chat_action(user_id, 'upload_document')
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Guardar temporalmente
        temp_file_path = os.path.join(TEMP_DIR, f"{user_id}_{original_name}")
        with open(temp_file_path, 'wb') as f:
            f.write(downloaded_file)
        
        # Información del archivo
        file_ext = Path(original_name).suffix
        file_icon = get_file_icon(file_ext)
        file_size_str = format_size(file_size)
        
        # Verificar si el usuario quiere renombrar
        user_state = USER_STATES.get(user_id, {})
        
        if user_state.get('state') == UserState.WAITING_RENAME:
            # Guardar archivo pendiente y pedir nuevo nombre
            USER_PENDING_FILES[user_id] = {
                'temp_path': temp_file_path,
                'original_name': original_name,
                'file_icon': file_icon,
                'file_size_str': file_size_str,
                'file_size': file_size
            }
            
            bot.send_message(user_id,
                            f"✏️ **Archivo recibido**\n\n"
                            f"Nombre actual: `{original_name}`\n"
                            f"Tamaño: {file_size_str}\n\n"
                            f"**Envía el nuevo nombre** para este archivo.\n"
                            f"Incluye la extensión (ej: `mi_archivo.txt`)",
                            parse_mode='Markdown')
            
            USER_STATES[user_id] = {'state': UserState.WAITING_FILE}
            
        else:
            # Enviar directamente
            send_file_with_thumbnail(
                user_id, 
                temp_file_path, 
                original_name, 
                file_icon, 
                file_size_str, 
                file_size
            )
            USER_STATES[user_id] = {'state': UserState.WAITING_FILE}
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Maneja mensajes de texto (para renombrar archivos)"""
    user_id = message.chat.id
    
    # Verificar si hay un archivo pendiente de renombrar
    if user_id in USER_PENDING_FILES:
        new_name = message.text.strip()
        
        if not new_name:
            bot.send_message(user_id, "❌ El nombre no puede estar vacío.")
            return
        
        # Validar nombre básico
        if '/' in new_name or '\\' in new_name or '..' in new_name:
            bot.send_message(user_id, "❌ Nombre inválido. No uses /, \\ o ..")
            return
        
        file_data = USER_PENDING_FILES[user_id]
        temp_path = file_data['temp_path']
        
        try:
            # Crear nuevo nombre con ruta temporal
            new_temp_path = os.path.join(TEMP_DIR, f"{user_id}_{new_name}")
            
            # Renombrar (copiar) el archivo
            shutil.copy2(temp_path, new_temp_path)
            
            # Eliminar el archivo temporal original
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # Enviar archivo renombrado
            send_file_with_thumbnail(
                user_id,
                new_temp_path,
                new_name,
                file_data['file_icon'],
                file_data['file_size_str'],
                file_data['file_size']
            )
            
            # Limpiar datos pendientes
            del USER_PENDING_FILES[user_id]
            
        except Exception as e:
            bot.send_message(user_id, f"❌ Error al renombrar: {str(e)}")
            if user_id in USER_PENDING_FILES:
                del USER_PENDING_FILES[user_id]
    
    else:
        # Mensaje normal
        bot.send_message(user_id,
                        "📁 **Instrucciones:**\n\n"
                        "1. Envía una **foto** para thumbnail (opcional)\n"
                        "2. Envía un **archivo** (hasta 50 MB)\n"
                        "3. Usa /rename antes de enviar para cambiar el nombre\n\n"
                        "Usa /help para más comandos.",
                        parse_mode='Markdown')

def send_file_with_thumbnail(user_id, file_path, file_name, file_icon, file_size_str, file_size):
    """Envía un archivo con thumbnail si está disponible"""
    try:
        # Verificar si el usuario tiene thumbnail
        user_has_thumbnail = user_id in USER_THUMBNAILS and os.path.exists(USER_THUMBNAILS[user_id])
        
        # Preparar caption
        caption = f"{file_icon} {file_name}\n📏 {file_size_str}"
        
        if user_has_thumbnail:
            # Enviar con thumbnail personalizado
            with open(USER_THUMBNAILS[user_id], 'rb') as thumb, \
                 open(file_path, 'rb') as file_data:
                
                bot.send_document(
                    chat_id=user_id,
                    document=file_data,
                    caption=caption,
                    visible_file_name=file_name,
                    thumbnail=thumb
                )
        else:
            # Enviar sin thumbnail personalizado
            with open(file_path, 'rb') as file_data:
                bot.send_document(
                    chat_id=user_id,
                    document=file_data,
                    caption=caption,
                    visible_file_name=file_name
                )
        
        # Confirmación
        thumb_status = "con tu thumbnail personalizado" if user_has_thumbnail else "sin thumbnail personalizado"
        bot.send_message(user_id,
                        f"✅ **Archivo enviado** {thumb_status}\n\n"
                        f"📁 `{file_name}`\n"
                        f"📊 {file_size_str}\n\n"
                        f"Envía otro archivo o usa /rename para el próximo.",
                        parse_mode='Markdown')
        
        # Limpiar archivo temporal
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        bot.send_message(user_id, f"❌ Error al enviar archivo: {str(e)}")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

if __name__ == '__main__':
    print("🤖 Bot de Archivos con Renombrado y Límite 50MB")
    print(f"📏 Límite por archivo: {MAX_FILE_SIZE / (1024*1024)} MB")
    print(f"📁 Directorio temporal: {TEMP_DIR}")
    
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR, ignore_errors=True)
