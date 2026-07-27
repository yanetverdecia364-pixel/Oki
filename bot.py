import os
import json
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters, 
    ContextTypes,
    ChatJoinRequestHandler,
    ChatMemberHandler
)

# ==================== CONFIGURACIÓN ====================
TOKEN = "8501732432:AAGbg4WpI1wtEChSTbbpmzOnhd5xdGFTnfQ"
ID_ADMIN = 5353490913

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ARCHIVO_CONFIG = "config.json"
ARCHIVO_REGISTRO = "registro.json"

config_default = {
    "grupos": {},
    "mensajes_bienvenida": [],  # Lista de hasta 3 mensajes
    "botones_bienvenida": [],
    "auto_aprobar": True,
    "tiempo_aprobacion": 0,
    "share_text": "🔞 Únete al mejor grupo +18 😏 🔥 https://kut.lat/eEva",
    "tiempo_entre_mensajes": 60,  # Segundos entre mensajes
    "tiempo_eliminacion": 0,
    "fijar_mensajes": False
}

def cargar_config():
    try:
        with open(ARCHIVO_CONFIG, "r") as f:
            return json.load(f)
    except:
        guardar_config(config_default)
        return config_default

def guardar_config(config):
    with open(ARCHIVO_CONFIG, "w") as f:
        json.dump(config, f, indent=4)

def cargar_registro():
    try:
        with open(ARCHIVO_REGISTRO, "r") as f:
            return json.load(f)
    except:
        return {"usuarios": {}}

def guardar_registro(registro):
    with open(ARCHIVO_REGISTRO, "w") as f:
        json.dump(registro, f, indent=4)

# ==================== OBTENER CONFIG DEL GRUPO ====================
def get_grupo_config(grupo_id):
    config = cargar_config()
    gid = str(grupo_id)
    
    if gid not in config.get('grupos', {}):
        config['grupos'][gid] = {
            "mensajes_bienvenida": [
                {"texto": "👋 <b>¡Bienvenido {MENTION}!</b>\n\nTe damos la bienvenida al grupo.", "media": None, "sticker": None, "botones": []},
                {"texto": "📌 <b>Segundo mensaje</b>\n\nRecuerda leer las reglas.", "media": None, "sticker": None, "botones": []},
                {"texto": "🎉 <b>¡Último mensaje!</b>\n\nDisfruta del grupo.", "media": None, "sticker": None, "botones": []}
            ],
            "botones_bienvenida": [],
            "auto_aprobar": True,
            "tiempo_aprobacion": 0,
            "share_text": config_default['share_text'],
            "tiempo_entre_mensajes": 60,
            "tiempo_eliminacion": 0,
            "fijar_mensajes": False
        }
        guardar_config(config)
    
    return config['grupos'][gid]

def guardar_grupo_config(grupo_id, grupo_config):
    config = cargar_config()
    config['grupos'][str(grupo_id)] = grupo_config
    guardar_config(config)

# ==================== VARIABLES ====================
def obtener_variables(user, chat=None, grupo_config=None):
    return {
        "{NAME}": user.first_name or "",
        "{MENTION}": f'<a href="tg://user?id={user.id}">{user.first_name or "Usuario"}</a>',
        "{USERNAME}": f"@{user.username}" if user.username else "",
        "{GROUPNAME}": chat.title if chat else "",
        "{DATE}": datetime.now().strftime("%d/%m/%Y"),
        "{TIME}": datetime.now().strftime("%H:%M"),
    }

def procesar_mensaje(texto, variables):
    for key, value in variables.items():
        texto = texto.replace(key, str(value))
    return texto

# ==================== CREAR BOTONES ====================
def crear_botones(botones_config, share_text=None):
    if not botones_config and not share_text:
        return None
    
    keyboard = []
    fila = []
    
    if share_text:
        fila.append(InlineKeyboardButton("📤 Compartir", switch_inline_query=share_text))
    
    for b in botones_config:
        if b.get('tipo') == 'url':
            fila.append(InlineKeyboardButton(b['texto'], url=b['url']))
        elif b.get('tipo') == 'alert':
            fila.append(InlineKeyboardButton(b['texto'], callback_data=f"alert_{b.get('alert_text', '¡Mensaje!')}"))
        elif b.get('tipo') == 'share':
            fila.append(InlineKeyboardButton(b['texto'], switch_inline_query=b.get('share_text', share_text or '¡Mira!')))
        elif b.get('tipo') == 'copy':
            fila.append(InlineKeyboardButton(b['texto'], callback_data=f"copy_{b.get('copy_text', 'Copiado')}"))
        
        if len(fila) >= 2:
            keyboard.append(fila)
            fila = []
    
    if fila:
        keyboard.append(fila)
    
    return InlineKeyboardMarkup(keyboard) if keyboard else None

# ==================== COMANDO START ====================
async def start(update, context):
    if update.effective_user.id != ID_ADMIN:
        await update.message.reply_text("❌ No tienes permiso.")
        return
    
    if update.message.chat.type in ['group', 'supergroup']:
        grupo_id = update.message.chat_id
        get_grupo_config(grupo_id)
        await update.message.reply_text(
            "🤖 *Configuración del grupo*\n\n"
            "La configuración se realiza en el chat privado.\n"
            "📌 Abre el chat privado con el bot y usa /start.",
            parse_mode="Markdown"
        )
        return
    
    config = cargar_config()
    grupos = config.get('grupos', {})
    
    if grupos:
        texto = "📋 *TUS GRUPOS:*\n\n"
        keyboard = []
        for gid in grupos:
            try:
                chat = await context.bot.get_chat(int(gid))
                nombre = chat.title or f"Grupo {gid}"
                keyboard.append([InlineKeyboardButton(f"📌 {nombre}", callback_data=f"menu_grupo_{gid}")])
            except:
                keyboard.append([InlineKeyboardButton(f"📌 Grupo {gid}", callback_data=f"menu_grupo_{gid}")])
        
        keyboard.append([InlineKeyboardButton("🔄 Actualizar", callback_data="menu_list_grupos")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.message.reply_text("🤖 *BOT*\n\nNo hay grupos configurados.")

# ==================== MENÚ PRINCIPAL ====================
async def menu_principal(update, context, edit=False, grupo_id=None):
    query = update.callback_query if edit else None
    
    if not grupo_id and query:
        grupo_id = query.message.chat_id
    elif not grupo_id and update.message:
        grupo_id = update.message.chat_id
    
    grupo_config = get_grupo_config(grupo_id)
    mensajes = grupo_config.get('mensajes_bienvenida', [])
    
    keyboard = [
        [InlineKeyboardButton("📝 Mensaje 1", callback_data=f"msg_edit_0_{grupo_id}")],
        [InlineKeyboardButton("📝 Mensaje 2", callback_data=f"msg_edit_1_{grupo_id}")],
        [InlineKeyboardButton("📝 Mensaje 3", callback_data=f"msg_edit_2_{grupo_id}")],
        [InlineKeyboardButton("🔘 Botones Globales", callback_data=f"botones_global_{grupo_id}")],
        [InlineKeyboardButton("⏰ Tiempo entre mensajes", callback_data=f"tiempo_entre_{grupo_id}")],
        [InlineKeyboardButton("⏰ Eliminar mensajes", callback_data=f"tiempo_eliminar_{grupo_id}")],
        [InlineKeyboardButton("📌 Fijar mensajes", callback_data=f"fijar_{grupo_id}")],
        [InlineKeyboardButton("✅ Auto-Aprobación", callback_data=f"auto_{grupo_id}")],
        [InlineKeyboardButton("⏰ Tiempo Aprobación", callback_data=f"tiempo_aprobacion_{grupo_id}")],
        [InlineKeyboardButton("📤 Texto Compartir", callback_data=f"share_{grupo_id}")],
        [InlineKeyboardButton("👁️ Vista Previa", callback_data=f"preview_{grupo_id}")],
        [InlineKeyboardButton("📋 Listar Grupos", callback_data="menu_list_grupos")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    texto = (
        f"🤖 *CONFIGURACIÓN*\n\n"
        f"📌 Grupo: `{grupo_id}`\n"
        f"📝 Mensajes: {len(mensajes)}\n"
        f"⏰ Entre mensajes: {grupo_config.get('tiempo_entre_mensajes', 60)}s\n"
        f"⏰ Eliminar: {grupo_config.get('tiempo_eliminacion', 0)}s\n"
        f"📌 Fijar: {'✅' if grupo_config.get('fijar_mensajes', False) else '❌'}\n"
        f"✅ Auto-Aprobación: {'ON' if grupo_config.get('auto_aprobar', True) else 'OFF'}\n\n"
        f"Selecciona una opción:"
    )
    
    if edit and query:
        await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
        await query.answer()
    else:
        await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=reply_markup)

# ==================== MENÚ EDITAR MENSAJE ====================
async def msg_edit(update, context, grupo_id, index):
    query = update.callback_query
    grupo_config = get_grupo_config(grupo_id)
    mensajes = grupo_config.get('mensajes_bienvenida', [])
    
    if index >= len(mensajes):
        await query.edit_message_text("❌ Mensaje no existe.")
        return
    
    msg = mensajes[index]
    
    keyboard = [
        [InlineKeyboardButton("📝 Editar Texto", callback_data=f"msg_text_{index}_{grupo_id}")],
        [InlineKeyboardButton("🖼️ Multimedia", callback_data=f"msg_media_{index}_{grupo_id}")],
        [InlineKeyboardButton("⭐ Sticker", callback_data=f"msg_sticker_{index}_{grupo_id}")],
        [InlineKeyboardButton("🔘 Botones", callback_data=f"msg_botones_{index}_{grupo_id}")],
        [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📝 *Mensaje {index+1}*\n\n"
        f"Texto: {msg.get('texto', '')[:50]}...\n"
        f"Media: {'✅' if msg.get('media') else '❌'}\n"
        f"Sticker: {'✅' if msg.get('sticker') else '❌'}\n"
        f"Botones: {len(msg.get('botones', []))}\n\n"
        f"Selecciona qué editar:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await query.answer()

# ==================== CALLBACKS ====================
async def menu_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ID_ADMIN:
        await query.edit_message_text("❌ No tienes permiso.")
        return
    
    data = query.data
    
    if data.startswith("alert_"):
        await query.answer(data.replace('alert_', ''), show_alert=True)
        return
    
    if data.startswith("copy_"):
        await query.answer(f"📋 Copiado:\n{data.replace('copy_', '')}", show_alert=True)
        return
    
    if data == "menu_list_grupos":
        await listar_grupos(update, context)
        return
    
    if data.startswith("menu_grupo_"):
        grupo_id = data.replace("menu_grupo_", "")
        await menu_principal(update, context, edit=True, grupo_id=int(grupo_id))
        return
    
    parts = data.split('_')
    if len(parts) < 2:
        return
    
    grupo_id = parts[-1]
    try:
        grupo_id = int(grupo_id)
    except:
        return
    
    grupo_config = get_grupo_config(grupo_id)
    config = cargar_config()
    
    # ========== EDITAR MENSAJE ==========
    if data.startswith("msg_edit_"):
        index = int(parts[2])
        await msg_edit(update, context, grupo_id, index)
        return
    
    # ========== EDITAR TEXTO ==========
    if data.startswith("msg_text_"):
        index = int(parts[2])
        await query.edit_message_text(
            f"✏️ *Editar Mensaje {index+1}*\n\n"
            "Envía el nuevo texto.\n\n"
            "Formatos HTML:\n"
            "• `<b>bold</b>`\n"
            "• `<i>italic</i>`\n"
            "• `<spoiler>spoiler</spoiler>`\n"
            "• `<blockquote>quote</blockquote>`\n\n"
            "Variables: `{NAME}`, `{MENTION}`, `{USERNAME}`, `{GROUPNAME}`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = f'msg_text_{index}'
        context.user_data['grupo_id'] = grupo_id
        return
    
    # ========== MULTIMEDIA ==========
    if data.startswith("msg_media_"):
        index = int(parts[2])
        await query.edit_message_text(
            f"🖼️ *Multimedia Mensaje {index+1}*\n\n"
            "Envía la foto o video que deseas usar.\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = f'msg_media_{index}'
        context.user_data['grupo_id'] = grupo_id
        return
    
    # ========== STICKER ==========
    if data.startswith("msg_sticker_"):
        index = int(parts[2])
        await query.edit_message_text(
            f"⭐ *Sticker Mensaje {index+1}*\n\n"
            "Envía el sticker que deseas usar.\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = f'msg_sticker_{index}'
        context.user_data['grupo_id'] = grupo_id
        return
    
    # ========== BOTONES DEL MENSAJE ==========
    if data.startswith("msg_botones_"):
        index = int(parts[2])
        await query.edit_message_text(
            f"🔘 *Botones Mensaje {index+1}*\n\n"
            "Envía los botones:\n"
            "• Normal: `Título - t.me/enlace`\n"
            "• Popup: `Título - popup:Texto`\n"
            "• Share: `Título - share:Texto`\n"
            "• Copy: `Título - copy:Texto`\n\n"
            "Ejemplo:\n"
            "`📢 Canal - t.me/canal`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = f'msg_botones_{index}'
        context.user_data['grupo_id'] = grupo_id
        return
    
    # ========== BOTONES GLOBALES ==========
    if data.startswith("botones_global_"):
        await query.edit_message_text(
            "🔘 *Botones Globales*\n\n"
            "Estos botones aparecerán en TODOS los mensajes.\n\n"
            "Envía los botones:\n"
            "• Normal: `Título - t.me/enlace`\n"
            "• Popup: `Título - popup:Texto`\n\n"
            "Ejemplo:\n"
            "`📢 Canal - t.me/canal`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'botones_globales'
        context.user_data['grupo_id'] = grupo_id
        return
    
    # ========== TIEMPO ENTRE MENSAJES ==========
    if data.startswith("tiempo_entre_"):
        keyboard = [
            [InlineKeyboardButton("30s", callback_data=f"t_entre_30_{grupo_id}")],
            [InlineKeyboardButton("60s", callback_data=f"t_entre_60_{grupo_id}")],
            [InlineKeyboardButton("120s", callback_data=f"t_entre_120_{grupo_id}")],
            [InlineKeyboardButton("300s", callback_data=f"t_entre_300_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        actual = grupo_config.get('tiempo_entre_mensajes', 60)
        await query.edit_message_text(
            f"⏰ *Tiempo entre mensajes*\n\nActual: {actual}s\n\nSelecciona el tiempo entre cada mensaje de bienvenida:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("t_entre_"):
        segundos = int(parts[2])
        grupo_config['tiempo_entre_mensajes'] = segundos
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text(f"✅ Tiempo entre mensajes: {segundos}s")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    # ========== ELIMINAR MENSAJES ==========
    if data.startswith("tiempo_eliminar_"):
        keyboard = [
            [InlineKeyboardButton("❌ No eliminar (0s)", callback_data=f"t_elim_0_{grupo_id}")],
            [InlineKeyboardButton("⏰ 30s", callback_data=f"t_elim_30_{grupo_id}")],
            [InlineKeyboardButton("⏰ 60s", callback_data=f"t_elim_60_{grupo_id}")],
            [InlineKeyboardButton("⏰ 120s", callback_data=f"t_elim_120_{grupo_id}")],
            [InlineKeyboardButton("⏰ 300s", callback_data=f"t_elim_300_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        actual = grupo_config.get('tiempo_eliminacion', 0)
        await query.edit_message_text(
            f"🗑️ *Eliminar mensajes*\n\nActual: {actual}s\n\nLos mensajes se eliminarán después de este tiempo:\n0 = No eliminar",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("t_elim_"):
        segundos = int(parts[2])
        grupo_config['tiempo_eliminacion'] = segundos
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text(f"✅ Mensajes se eliminarán después de {segundos}s")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    # ========== FIJAR MENSAJES ==========
    if data.startswith("fijar_"):
        fijar = grupo_config.get('fijar_mensajes', False)
        keyboard = [
            [InlineKeyboardButton("✅ Activar" if not fijar else "✅ Ya Activado", callback_data=f"fijar_on_{grupo_id}")],
            [InlineKeyboardButton("❌ Desactivar" if fijar else "❌ Ya Desactivado", callback_data=f"fijar_off_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"📌 *Fijar mensajes*\n\nEstado: {'✅ Activado' if fijar else '❌ Desactivado'}\n\nLos mensajes se fijarán en el chat del usuario.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("fijar_on_"):
        grupo_config['fijar_mensajes'] = True
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("✅ Fijar mensajes ACTIVADO")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    if data.startswith("fijar_off_"):
        grupo_config['fijar_mensajes'] = False
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("❌ Fijar mensajes DESACTIVADO")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    # ========== AUTO-APROBACIÓN ==========
    if data.startswith("auto_"):
        auto = grupo_config.get('auto_aprobar', True)
        keyboard = [
            [InlineKeyboardButton("✅ Activar" if not auto else "✅ Ya Activado", callback_data=f"auto_on_{grupo_id}")],
            [InlineKeyboardButton("❌ Desactivar" if auto else "❌ Ya Desactivado", callback_data=f"auto_off_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"✅ *Auto-Aprobación*\n\nEstado: {'ON' if auto else 'OFF'}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("auto_on_"):
        grupo_config['auto_aprobar'] = True
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("✅ Auto-aprobación ACTIVADA")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    if data.startswith("auto_off_"):
        grupo_config['auto_aprobar'] = False
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("❌ Auto-aprobación DESACTIVADA")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    # ========== TIEMPO APROBACIÓN ==========
    if data.startswith("tiempo_aprobacion_"):
        keyboard = [
            [InlineKeyboardButton("⚡ Inmediata", callback_data=f"t_aprob_0_{grupo_id}")],
            [InlineKeyboardButton("⏰ 30s", callback_data=f"t_aprob_30_{grupo_id}")],
            [InlineKeyboardButton("⏰ 60s", callback_data=f"t_aprob_60_{grupo_id}")],
            [InlineKeyboardButton("⏰ 120s", callback_data=f"t_aprob_120_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        actual = grupo_config.get('tiempo_aprobacion', 0)
        await query.edit_message_text(
            f"⏰ *Tiempo de aprobación*\n\nActual: {actual}s\n\n0 = Inmediata",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("t_aprob_"):
        segundos = int(parts[2])
        grupo_config['tiempo_aprobacion'] = segundos
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text(f"✅ Tiempo de aprobación: {segundos}s")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    # ========== TEXTO COMPARTIR ==========
    if data.startswith("share_"):
        await query.edit_message_text(
            "📤 *Texto para Compartir*\n\n"
            "Envía el texto que aparecerá al usar COMPARTIR.\n\n"
            "Actual:\n`{}`\n\n"
            "Variables: `{GROUPNAME}`, `{NAME}`\n\n"
            "Para cancelar: /cancelar".format(grupo_config.get('share_text', 'No configurado')),
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'share_text'
        context.user_data['grupo_id'] = grupo_id
        return
    
    # ========== VISTA PREVIA ==========
    if data.startswith("preview_"):
        await preview_grupo(update, context, grupo_id)
        await query.delete_message()
        return
    
    if data.startswith("menu_back_"):
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return

# ==================== PREVIEW ====================
async def preview_grupo(update, context, grupo_id):
    grupo_config = get_grupo_config(grupo_id)
    mensajes = grupo_config.get('mensajes_bienvenida', [])
    botones_globales = grupo_config.get('botones_bienvenida', [])
    share_text = grupo_config.get('share_text', config_default['share_text'])
    
    variables = {
        "{NAME}": "Usuario",
        "{MENTION}": '<a href="tg://user?id=123">Usuario</a>',
        "{USERNAME}": "@usuario",
        "{GROUPNAME}": "Grupo de Prueba",
        "{DATE}": datetime.now().strftime("%d/%m/%Y"),
        "{TIME}": datetime.now().strftime("%H:%M"),
    }
    
    share_text_procesado = procesar_mensaje(share_text, variables)
    
    for i, msg in enumerate(mensajes):
        texto = procesar_mensaje(msg.get('texto', 'Mensaje sin texto'), variables)
        botones = msg.get('botones', []) + botones_globales
        reply_markup = crear_botones(botones, share_text_procesado)
        media = msg.get('media')
        sticker = msg.get('sticker')
        
        try:
            if media and media.get('file_id'):
                if media.get('tipo') == 'foto':
                    await update.callback_query.message.reply_photo(
                        photo=media.get('file_id'),
                        caption=f"👁️ *Mensaje {i+1}:*\n\n{texto}",
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )
            elif sticker:
                await update.callback_query.message.reply_sticker(sticker=sticker)
                await update.callback_query.message.reply_text(
                    f"👁️ *Mensaje {i+1}:*\n\n{texto}",
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            else:
                await update.callback_query.message.reply_text(
                    f"👁️ *Mensaje {i+1}:*\n\n{texto}",
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error preview: {str(e)}")

# ==================== LISTAR GRUPOS ====================
async def listar_grupos(update, context):
    query = update.callback_query
    config = cargar_config()
    grupos = config.get('grupos', {})
    
    if not grupos:
        await query.edit_message_text("📋 No hay grupos.")
        return
    
    texto = "📋 *TUS GRUPOS:*\n\n"
    keyboard = []
    for gid in grupos:
        try:
            chat = await context.bot.get_chat(int(gid))
            nombre = chat.title or f"Grupo {gid}"
            keyboard.append([InlineKeyboardButton(f"📌 {nombre}", callback_data=f"menu_grupo_{gid}")])
        except:
            keyboard.append([InlineKeyboardButton(f"📌 Grupo {gid}", callback_data=f"menu_grupo_{gid}")])
    
    keyboard.append([InlineKeyboardButton("🔄 Actualizar", callback_data="menu_list_grupos")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)

# ==================== COMANDOS ====================
async def cancelar(update, context):
    context.user_data.clear()
    await update.message.reply_text("✅ Cancelado.")

# ==================== MANEJO DE CONFIGURACIÓN ====================
async def handle_config(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    
    estado = context.user_data.get('esperando')
    if not estado:
        return
    
    grupo_id = context.user_data.get('grupo_id')
    if not grupo_id:
        await update.message.reply_text("❌ Error: no hay grupo.")
        return
    
    grupo_config = get_grupo_config(grupo_id)
    
    # ========== EDITAR TEXTO ==========
    if estado.startswith('msg_text_'):
        index = int(estado.split('_')[2])
        mensajes = grupo_config.get('mensajes_bienvenida', [])
        if index < len(mensajes):
            mensajes[index]['texto'] = update.message.text
            guardar_grupo_config(grupo_id, grupo_config)
            await update.message.reply_text("✅ Mensaje actualizado.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return
    
    # ========== MULTIMEDIA ==========
    if estado.startswith('msg_media_'):
        index = int(estado.split('_')[2])
        mensajes = grupo_config.get('mensajes_bienvenida', [])
        if index < len(mensajes):
            if update.message.photo:
                mensajes[index]['media'] = {"tipo": "foto", "file_id": update.message.photo[-1].file_id}
                guardar_grupo_config(grupo_id, grupo_config)
                await update.message.reply_text("✅ Foto guardada.")
            elif update.message.video:
                mensajes[index]['media'] = {"tipo": "video", "file_id": update.message.video.file_id}
                guardar_grupo_config(grupo_id, grupo_config)
                await update.message.reply_text("✅ Video guardado.")
            else:
                await update.message.reply_text("❌ Envía una foto o video.")
                return
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return
    
    # ========== STICKER ==========
    if estado.startswith('msg_sticker_'):
        index = int(estado.split('_')[2])
        mensajes = grupo_config.get('mensajes_bienvenida', [])
        if index < len(mensajes) and update.message.sticker:
            mensajes[index]['sticker'] = update.message.sticker.file_id
            guardar_grupo_config(grupo_id, grupo_config)
            await update.message.reply_text("✅ Sticker guardado.")
        else:
            await update.message.reply_text("❌ Envía un sticker.")
            return
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return
    
    # ========== BOTONES DEL MENSAJE ==========
    if estado.startswith('msg_botones_'):
        index = int(estado.split('_')[2])
        mensajes = grupo_config.get('mensajes_bienvenida', [])
        if index < len(mensajes):
            botones = procesar_botones(update.message.text)
            if botones:
                mensajes[index]['botones'] = botones
                guardar_grupo_config(grupo_id, grupo_config)
                await update.message.reply_text(f"✅ {len(botones)} botones agregados")
            else:
                await update.message.reply_text("❌ Formato incorrecto.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return
    
    # ========== BOTONES GLOBALES ==========
    if estado == 'botones_globales':
        botones = procesar_botones(update.message.text)
        if botones:
            grupo_config['botones_bienvenida'] = botones
            guardar_grupo_config(grupo_id, grupo_config)
            await update.message.reply_text(f"✅ {len(botones)} botones globales agregados")
        else:
            await update.message.reply_text("❌ Formato incorrecto.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return
    
    # ========== SHARE TEXT ==========
    if estado == 'share_text':
        grupo_config['share_text'] = update.message.text
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text("✅ Texto compartir actualizado.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return

# ==================== PROCESAR BOTONES ====================
def procesar_botones(texto):
    if not texto:
        return []
    
    botones = []
    for linea in texto.strip().split('\n'):
        if ' - ' in linea:
            partes = linea.strip().split(' - ', 1)
            titulo = partes[0].strip()
            accion = partes[1].strip()
            
            if accion.startswith('popup:') or accion.startswith('alert:'):
                botones.append({"tipo": "alert", "texto": titulo, "alert_text": accion.replace('popup:', '').replace('alert:', '')})
            elif accion.startswith('share:'):
                botones.append({"tipo": "share", "texto": titulo, "share_text": accion.replace('share:', '')})
            elif accion.startswith('copy:'):
                botones.append({"tipo": "copy", "texto": titulo, "copy_text": accion.replace('copy:', '')})
            elif accion.startswith('t.me/') or accion.startswith('https://'):
                if not accion.startswith('http'):
                    accion = 'https://' + accion
                botones.append({"tipo": "url", "texto": titulo, "url": accion})
    
    return botones

# ==================== SOLICITUDES DE UNIÓN ====================
async def handle_join_request(update, context):
    try:
        if not update.chat_join_request:
            return
            
        join_request = update.chat_join_request
        user = join_request.from_user
        chat = join_request.chat
        grupo_id = chat.id
        
        grupo_config = get_grupo_config(grupo_id)
        share_text = grupo_config.get('share_text', config_default['share_text'])
        mensajes = grupo_config.get('mensajes_bienvenida', [])
        botones_globales = grupo_config.get('botones_bienvenida', [])
        tiempo_entre = grupo_config.get('tiempo_entre_mensajes', 60)
        tiempo_eliminar = grupo_config.get('tiempo_eliminacion', 0)
        fijar = grupo_config.get('fijar_mensajes', False)
        
        variables = obtener_variables(user, chat, grupo_config)
        share_text_procesado = procesar_mensaje(share_text, variables)
        
        logger.info(f"🔵 Enviando {len(mensajes)} mensajes a {user.first_name}")
        
        # Enviar mensajes escalonados
        for i, msg in enumerate(mensajes):
            texto = procesar_mensaje(msg.get('texto', 'Mensaje sin texto'), variables)
            botones = msg.get('botones', []) + botones_globales
            reply_markup = crear_botones(botones, share_text_procesado)
            media = msg.get('media')
            sticker = msg.get('sticker')
            
            try:
                if media and media.get('file_id'):
                    if media.get('tipo') == 'foto':
                        sent_msg = await context.bot.send_photo(
                            chat_id=user.id,
                            photo=media.get('file_id'),
                            caption=texto,
                            parse_mode="HTML",
                            reply_markup=reply_markup,
                            protect_content=True
                        )
                    elif media.get('tipo') == 'video':
                        sent_msg = await context.bot.send_video(
                            chat_id=user.id,
                            video=media.get('file_id'),
                            caption=texto,
                            parse_mode="HTML",
                            reply_markup=reply_markup,
                            protect_content=True
                        )
                elif sticker:
                    await context.bot.send_sticker(chat_id=user.id, sticker=sticker, protect_content=True)
                    sent_msg = await context.bot.send_message(
                        chat_id=user.id,
                        text=texto,
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                        protect_content=True
                    )
                else:
                    sent_msg = await context.bot.send_message(
                        chat_id=user.id,
                        text=texto,
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                        protect_content=True
                    )
                
                logger.info(f"✅ Mensaje {i+1} enviado a {user.first_name}")
                
                # Fijar mensaje
                if fijar:
                    try:
                        await context.bot.pin_chat_message(chat_id=user.id, message_id=sent_msg.message_id)
                        logger.info(f"📌 Mensaje {i+1} fijado")
                    except Exception as e:
                        logger.error(f"Error fijando: {str(e)}")
                
                # Eliminar mensaje después de tiempo
                if tiempo_eliminar > 0:
                    async def eliminar_msg():
                        await asyncio.sleep(tiempo_eliminar)
                        try:
                            await context.bot.delete_message(chat_id=user.id, message_id=sent_msg.message_id)
                            logger.info(f"🗑️ Mensaje {i+1} eliminado")
                        except Exception as e:
                            logger.error(f"Error eliminando: {str(e)}")
                    asyncio.create_task(eliminar_msg())
                
                # Esperar entre mensajes (excepto el último)
                if i < len(mensajes) - 1 and tiempo_entre > 0:
                    logger.info(f"⏰ Esperando {tiempo_entre}s antes del siguiente mensaje")
                    await asyncio.sleep(tiempo_entre)
                
            except Exception as e:
                logger.error(f"Error enviando mensaje {i+1}: {str(e)}")
        
        # Auto-aprobación
        auto_aprobar = grupo_config.get('auto_aprobar', True)
        tiempo_aprobacion = grupo_config.get('tiempo_aprobacion', 0)
        
        if auto_aprobar:
            if tiempo_aprobacion > 0:
                async def aprobar_despues():
                    await asyncio.sleep(tiempo_aprobacion)
                    try:
                        await context.bot.approve_chat_join_request(chat_id=grupo_id, user_id=user.id)
                        logger.info(f"✅ {user.first_name} aprobado")
                    except Exception as e:
                        logger.error(f"Error aprobando: {str(e)}")
                asyncio.create_task(aprobar_despues())
            else:
                try:
                    await context.bot.approve_chat_join_request(chat_id=grupo_id, user_id=user.id)
                    logger.info(f"✅ {user.first_name} aprobado inmediatamente")
                except Exception as e:
                    logger.error(f"Error aprobando: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error en handle_join_request: {str(e)}")

# ==================== SALIDA DEL GRUPO ====================
async def handle_chat_member_update(update, context):
    try:
        if not update.chat_member:
            return
        
        chat_member = update.chat_member
        user = chat_member.user
        chat = update.effective_chat
        
        if not chat or chat.type not in ['group', 'supergroup']:
            return
        
        grupo_id = chat.id
        
        if chat_member.old_chat_member.status in ['member', 'administrator', 'creator'] and chat_member.new_chat_member.status in ['left', 'kicked']:
            grupo_config = get_grupo_config(grupo_id)
            variables = obtener_variables(user, chat, grupo_config)
            mensaje = config_default['mensaje_despedida']
            mensaje_personalizado = procesar_mensaje(mensaje, variables)
            
            try:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"👋 ¡Hasta luego!\n\n{mensaje_personalizado}",
                    parse_mode="HTML",
                    protect_content=True
                )
                logger.info(f"✅ Despedida enviada a {user.first_name}")
            except:
                pass
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")

async def borrar_mensajes_usuario(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    
    if update.message.chat.type != 'private':
        return
    
    try:
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
        logger.info("🗑️ Mensaje de usuario borrado")
    except:
        pass

# ==================== INICIO ====================
def main():
    logger.info("🚀 Iniciando Bot...")
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancelar", cancelar))
    
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="menu_|msg_|botones_|tiempo_|t_|fijar_|auto_|share_|preview_|alert_|copy_"))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_config))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Sticker & ~filters.COMMAND, handle_config))
    
    application.add_handler(MessageHandler(filters.ALL & filters.ChatType.PRIVATE, borrar_mensajes_usuario))
    
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    application.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    
    logger.info("✅ Bot iniciado correctamente!")
    logger.info(f"👤 Admin ID: {ID_ADMIN}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
