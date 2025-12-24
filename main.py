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
API_TOKEN = '8562042457:AAGA__pfWDMVfdslzqwnoFl4yLrAre-HJ5I'  # Reemplaza con tu token de bot
bot = telebot.TeleBot(API_TOKEN)

# Directorios y estados
TEMP_DIR = tempfile.mkdtemp(prefix='telegram_bot_')
USER_STATES = defaultdict(dict)  # {user_id: {'state': '', 'data': {}}}

# Estados del usuario
class UserState:
    WAITING_FILE = 'waiting_file'
    WAITING_THUMBNAIL = 'waiting_thumbnail'
    WAITING_NEW_NAME = 'waiting_new_name'
    CONFIRM_RENAME = 'confirm_rename'

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Maneja los comandos /start y /help"""
    welcome_text = """
🤖 **Bot Universal de Archivos**

¡Hola! Soy un bot que puede manejar **CUALQUIER tipo de archivo** que exista.

📁 **Acepto absolutamente todo:**
• APK, EXE, DMG, APP (ejecutables)
• ZIP, RAR, 7Z, TAR (comprimidos)
• ISO, IMG, VMDK (imágenes de disco)
• PY, JS, JAVA, CPP (código fuente)
• DB, SQLITE, MDB (bases de datos)
• Y **CUALQUIER OTRA EXTENSIÓN** que exista

🔄 **Cómo funciona:**
1. Envíame cualquier archivo (sin límites de tipo)
2. Opcional: Envía una foto como thumbnail personalizado
3. Opcional: Renombra el archivo como quieras
4. Recibe tu archivo de vuelta con thumbnail

📤 **Comandos disponibles:**
/start - Muestra este mensaje
/cancel - Cancela la operación actual
/status - Muestra información del bot

⚠️ **Notas:**
• Archivos hasta 2GB (límite de Telegram)
• Tu thumbnail personalizado se usará si lo envías
• Puedes renombrar el archivo antes de recibirlo
"""
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')
    USER_STATES[message.chat.id] = {'state': UserState.WAITING_FILE}

@bot.message_handler(commands=['cancel'])
def cancel_operation(message):
    """Cancela la operación actual"""
    USER_STATES[message.chat.id] = {'state': UserState.WAITING_FILE}
    bot.send_message(message.chat.id, "❌ Operación cancelada. Puedes enviar un nuevo archivo.")

@bot.message_handler(commands=['status'])
def bot_status(message):
    """Muestra el estado del bot"""
    status_text = f"""
🤖 **Estado del Bot**
    
📊 **Usuarios activos:** {len(USER_STATES)}
💾 **Directorio temporal:** {TEMP_DIR}
🔄 **Estado actual:** {USER_STATES.get(message.chat.id, {}).get('state', 'waiting_file')}

✅ **Listo para recibir cualquier archivo**
⚠️ **Advertencia:** Archivos temporales se eliminan automáticamente
"""
    bot.send_message(message.chat.id, status_text, parse_mode='Markdown')

def get_file_info(file_path):
    """Obtiene información detallada de cualquier archivo"""
    try:
        path = Path(file_path)
        stats = os.stat(file_path)
        
        # Detectar MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'application/octet-stream'  # Tipo binario por defecto
        
        # Tamaño legible
        size = stats.st_size
        size_readable = format_size(size)
        
        # Fecha de modificación
        mod_time = datetime.fromtimestamp(stats.st_mtime)
        
        # Icono según extensión
        extension = path.suffix.lower()
        icon = get_file_icon(extension)
        
        return {
            'name': path.name,
            'extension': extension,
            'size': size,
            'size_readable': size_readable,
            'mime_type': mime_type,
            'modified': mod_time.strftime('%Y-%m-%d %H:%M:%S'),
            'icon': icon,
            'path': str(path)
        }
    except Exception as e:
        return None

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
        # Ejecutables
        '.apk': '🤖', '.exe': '⚙️', '.app': '🍎', '.dmg': '🍎', '.msi': '🔧',
        '.deb': '🐧', '.rpm': '🐧', '.sh': '🐚', '.bat': '🪟', '.cmd': '🪟',
        
        # Comprimidos
        '.zip': '🗜️', '.rar': '🗜️', '.7z': '🗜️', '.tar': '🗜️', '.gz': '🗜️',
        '.bz2': '🗜️', '.xz': '🗜️', '.tgz': '🗜️',
        
        # Discos/imágenes
        '.iso': '💿', '.img': '💿', '.vmdk': '💿', '.dmg': '💿', '.toast': '💿',
        
        # Código fuente
        '.py': '🐍', '.js': '📜', '.java': '☕', '.cpp': '🔧', '.c': '🔧',
        '.html': '🌐', '.css': '🎨', '.php': '🐘', '.rb': '💎', '.go': '🐹',
        '.rs': '🦀', '.swift': '🐦', '.kt': '🤖', '.dart': '🎯',
        
        # Documentos
        '.pdf': '📕', '.doc': '📘', '.docx': '📘', '.xls': '📗', '.xlsx': '📗',
        '.ppt': '📙', '.pptx': '📙', '.txt': '📝', '.rtf': '📝', '.md': '📝',
        
        # Bases de datos
        '.db': '🗃️', '.sqlite': '🗃️', '.sql': '🗃️', '.mdb': '🗃️', '.accdb': '🗃️',
        
        # Configuración
        '.json': '📊', '.xml': '📄', '.yml': '⚙️', '.yaml': '⚙️', '.ini': '⚙️',
        '.conf': '⚙️', '.cfg': '⚙️',
        
        # Multimedia
        '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵', '.mp4': '🎬', '.avi': '🎬',
        '.mkv': '🎬', '.mov': '🎬', '.jpg': '🖼️', '.png': '🖼️', '.gif': '🖼️',
        
        # Otros comunes
        '.torrent': '🧲', '.lnk': '🔗', '.url': '🔗',
    }
    
    return icon_map.get(extension, '📁')  # 📁 por defecto para cualquier extensión no listada

@bot.message_handler(content_types=['document'])
def handle_document(message):
    """Maneja CUALQUIER documento enviado"""
    chat_id = message.chat.id
    
    try:
        # Obtener información del archivo
        file_info = bot.get_file(message.document.file_id)
        original_name = message.document.file_name or f"archivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Descargar el archivo
        bot.send_message(chat_id, f"📥 Descargando: `{original_name}`...", parse_mode='Markdown')
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Guardar en temporal
        temp_path = os.path.join(TEMP_DIR, original_name)
        with open(temp_path, 'wb') as f:
            f.write(downloaded_file)
        
        # Obtener información detallada
        file_data = get_file_info(temp_path)
        
        if not file_data:
            bot.send_message(chat_id, "❌ Error al obtener información del archivo")
            return
        
        # Mostrar información del archivo
        info_text = f"""
{file_data['icon']} **Archivo Recibido**

📄 **Nombre:** `{file_data['name']}`
🔤 **Extensión:** `{file_data['extension'] or 'Sin extensión'}`
📦 **Tipo MIME:** `{file_data['mime_type']}`
📏 **Tamaño:** `{file_data['size_readable']}`
🕒 **Modificado:** `{file_data['modified']}`
📊 **Bytes:** `{file_data['size']:,}`

¿Qué deseas hacer ahora?
"""
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.row(
            telebot.types.InlineKeyboardButton("🖼️ Enviar Thumbnail", callback_data=f"send_thumb_{original_name}"),
            telebot.types.InlineKeyboardButton("✏️ Renombrar", callback_data=f"rename_{original_name}")
        )
        keyboard.row(
            telebot.types.InlineKeyboardButton("✅ Enviar Así", callback_data=f"send_as_is_{original_name}"),
            telebot.types.InlineKeyboardButton("❌ Cancelar", callback_data="cancel")
        )
        
        # Guardar estado y datos
        USER_STATES[chat_id] = {
            'state': UserState.WAITING_THUMBNAIL,
            'file_path': temp_path,
            'file_data': file_data,
            'original_name': original_name
        }
        
        bot.send_message(chat_id, info_text, parse_mode='Markdown', reply_markup=keyboard)
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error procesando el archivo: {str(e)}")
        print(f"Error: {e}")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """Maneja fotos enviadas como thumbnails"""
    chat_id = message.chat.id
    user_state = USER_STATES.get(chat_id, {})
    
    if user_state.get('state') != UserState.WAITING_THUMBNAIL:
        return
    
    try:
        # Obtener la foto de mejor calidad
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_photo = bot.download_file(file_info.file_path)
        
        # Guardar thumbnail
        thumb_path = os.path.join(TEMP_DIR, f"thumbnail_{chat_id}.jpg")
        with open(thumb_path, 'wb') as f:
            f.write(downloaded_photo)
        
        # Actualizar estado
        user_state['thumbnail_path'] = thumb_path
        USER_STATES[chat_id] = user_state
        
        bot.send_message(chat_id, "✅ Thumbnail recibido. ¿Deseas renombrar el archivo?", 
                        reply_markup=get_rename_keyboard())
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error procesando thumbnail: {str(e)}")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Maneja texto para renombrar archivos"""
    chat_id = message.chat.id
    user_state = USER_STATES.get(chat_id, {})
    
    if user_state.get('state') == UserState.WAITING_NEW_NAME:
        new_name = message.text.strip()
        original_path = user_state['file_path']
        
        # Validar nombre
        if not new_name:
            bot.send_message(chat_id, "❌ El nombre no puede estar vacío")
            return
        
        # Asegurar extensión si no la tiene
        original_ext = Path(original_path).suffix
        if not Path(new_name).suffix and original_ext:
            new_name += original_ext
        
        # Crear nueva ruta
        new_path = os.path.join(TEMP_DIR, new_name)
        
        try:
            # Renombrar (copiar)
            shutil.copy2(original_path, new_path)
            
            # Actualizar estado
            user_state['file_path'] = new_path
            user_state['new_name'] = new_name
            user_state['state'] = UserState.CONFIRM_RENAME
            USER_STATES[chat_id] = user_state
            
            bot.send_message(chat_id, f"✅ Archivo renombrado a: `{new_name}`\n\n¿Listo para enviar?", 
                            parse_mode='Markdown',
                            reply_markup=get_final_keyboard())
            
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error renombrando archivo: {str(e)}")

def get_rename_keyboard():
    """Teclado para opciones después de thumbnail"""
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton("✏️ Sí, Renombrar", callback_data="yes_rename"),
        telebot.types.InlineKeyboardButton("✅ No, Enviar Así", callback_data="no_rename")
    )
    return keyboard

def get_final_keyboard():
    """Teclado final para enviar archivo"""
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton("🚀 Enviar Archivo", callback_data="send_file"),
        telebot.types.InlineKeyboardButton("❌ Cancelar", callback_data="cancel")
    )
    return keyboard

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Maneja todos los callbacks"""
    chat_id = call.message.chat.id
    user_state = USER_STATES.get(chat_id, {})
    
    try:
        if call.data == "cancel":
            USER_STATES[chat_id] = {'state': UserState.WAITING_FILE}
            bot.edit_message_text("❌ Operación cancelada", chat_id, call.message.message_id)
            return
            
        elif call.data.startswith("send_thumb_"):
            filename = call.data[11:]
            bot.edit_message_text(
                f"📤 Por favor, envía una foto para usar como thumbnail para `{filename}`",
                chat_id, call.message.message_id,
                parse_mode='Markdown'
            )
            
        elif call.data.startswith("rename_"):
            filename = call.data[7:]
            user_state['state'] = UserState.WAITING_NEW_NAME
            USER_STATES[chat_id] = user_state
            bot.edit_message_text(
                f"✏️ Escribe el nuevo nombre para `{filename}`\n\n⚠️ Incluye la extensión o se mantendrá la original",
                chat_id, call.message.message_id,
                parse_mode='Markdown'
            )
            
        elif call.data.startswith("send_as_is_"):
            send_file_to_user(chat_id, user_state)
            
        elif call.data == "yes_rename":
            user_state['state'] = UserState.WAITING_NEW_NAME
            USER_STATES[chat_id] = user_state
            bot.edit_message_text(
                "✏️ Escribe el nuevo nombre para el archivo\n\n⚠️ Incluye la extensión o se mantendrá la original",
                chat_id, call.message.message_id
            )
            
        elif call.data == "no_rename":
            send_file_to_user(chat_id, user_state)
            
        elif call.data == "send_file":
            send_file_to_user(chat_id, user_state)
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)}")

def send_file_to_user(chat_id, user_state):
    """Envía el archivo procesado al usuario"""
    try:
        file_path = user_state.get('file_path')
        thumbnail_path = user_state.get('thumbnail_path')
        file_data = user_state.get('file_data', {})
        
        if not file_path or not os.path.exists(file_path):
            bot.send_message(chat_id, "❌ Archivo no encontrado")
            return
        
        # Preparar caption
        caption = f"{file_data.get('icon', '📁')} `{Path(file_path).name}`\n"
        caption += f"📏 {file_data.get('size_readable', 'N/A')} • {file_data.get('mime_type', 'Unknown')}"
        
        # Enviar thumbnail si existe
        if thumbnail_path and os.path.exists(thumbnail_path):
            with open(thumbnail_path, 'rb') as thumb:
                bot.send_photo(chat_id, thumb, caption="🖼️ Thumbnail personalizado")
        
        # Enviar archivo
        with open(file_path, 'rb') as file:
            bot.send_document(chat_id, file, caption=caption, parse_mode='Markdown')
        
        bot.send_message(chat_id, "✅ ¡Archivo enviado exitosamente!\n\nPuedes enviar otro archivo cuando quieras.")
        
        # Limpiar
        clean_temp_files(file_path, thumbnail_path)
        USER_STATES[chat_id] = {'state': UserState.WAITING_FILE}
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error enviando archivo: {str(e)}")

def clean_temp_files(*paths):
    """Limpia archivos temporales"""
    for path in paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

# Limpieza periódica de archivos viejos
def cleanup_old_files():
    """Limpia archivos temporales más viejos de 1 hora"""
    try:
        for item in os.listdir(TEMP_DIR):
            item_path = os.path.join(TEMP_DIR, item)
            if os.path.isfile(item_path):
                # Si el archivo tiene más de 1 hora
                if os.path.getmtime(item_path) < (time.time() - 3600):
                    os.remove(item_path)
    except:
        pass

@bot.message_handler(content_types=['video', 'audio', 'voice', 'sticker', 'animation'])
def handle_other_files(message):
    """Maneja otros tipos de archivos (opcional)"""
    chat_id = message.chat.id
    bot.send_message(chat_id, "📁 Por favor, envía el archivo como **Documento** para preservar el formato original.\n\nUsa el clip 📎 y selecciona 'Documento' en Telegram.")

if __name__ == '__main__':
    print("🤖 Bot Universal de Archivos Iniciado")
    print(f"📁 Directorio temporal: {TEMP_DIR}")
    print("✅ Listo para recibir CUALQUIER tipo de archivo")
    print("🔧 APK, EXE, ZIP, ISO, PY, y cualquier otra extensión soportada")
    
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Limpieza final
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR, ignore_errors=True)
