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
TOKEN = "8501732432:AAHcvGDBfC-c3B0JerQu8tp0A-EQrfBjpNQ"
ID_ADMIN = 5353490913

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ARCHIVO_CONFIG = "config.json"
ARCHIVO_REGISTRO = "registro.json"

config_default = {
    "grupos": {},
    "mensaje_bienvenida": "¡Bienvenido al grupo! 🎉\n\nTe damos la bienvenida a nuestra comunidad.",
    "mensaje_reingreso": "¡Bienvenido de nuevo {NAME}! 🎉\n\nNos alegra verte otra vez.",
    "mensaje_despedida": "¡Hasta luego {NAME}! 👋\n\nEsperamos verte pronto.",
    "botones_bienvenida": [],
    "botones_despedida": [],
    "botones_repetidos": [],
    "media_bienvenida": None,
    "media_reingreso": None,
    "media_despedida": None,
    "sticker_bienvenida": None,
    "sticker_reingreso": None,
    "sticker_despedida": None,
    "gif_bienvenida": None,
    "gif_reingreso": None,
    "gif_despedida": None,
    "mensajes_programados": [],
    "formato_texto": "html",
    "auto_aprobar": True,
    "tiempo_aprobacion": 0,
    "borrar_mensajes_pv": True,
    "proteger_mensajes": True,
    "tiempo_borrado_pv": 60,
    "tiempo_eliminacion_bienvenida": 0,
    "fijar_mensaje": False,
    "reglas": ""
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
            "mensaje_bienvenida": config_default['mensaje_bienvenida'],
            "mensaje_reingreso": config_default['mensaje_reingreso'],
            "mensaje_despedida": config_default['mensaje_despedida'],
            "botones_bienvenida": [],
            "botones_despedida": [],
            "botones_repetidos": [],
            "media_bienvenida": None,
            "media_reingreso": None,
            "media_despedida": None,
            "sticker_bienvenida": None,
            "sticker_reingreso": None,
            "sticker_despedida": None,
            "gif_bienvenida": None,
            "gif_reingreso": None,
            "gif_despedida": None,
            "auto_aprobar": True,
            "tiempo_aprobacion": 0,
            "mensajes_programados": [],
            "tiempo_eliminacion_bienvenida": 0,
            "mensajes_activos": {},
            "fijar_mensaje": False,
            "reglas": ""
        }
        guardar_config(config)
    
    return config['grupos'][gid]

def guardar_grupo_config(grupo_id, grupo_config):
    config = cargar_config()
    config['grupos'][str(grupo_id)] = grupo_config
    guardar_config(config)

# ==================== VARIABLES PARA MENSAJES ====================
def obtener_variables(user, chat=None, grupo_config=None):
    variables = {
        "{ID}": str(user.id),
        "{NAME}": user.first_name or "",
        "{SURNAME}": user.last_name or "",
        "{NAMESURNAME}": f"{user.first_name or ''} {user.last_name or ''}".strip(),
        "{USERNAME}": f"@{user.username}" if user.username else "",
        "{MENTION}": f'<a href="tg://user?id={user.id}">{user.first_name or "Usuario"}</a>',
        "{LANG}": user.language_code or "es",
        "{DATE}": datetime.now().strftime("%d/%m/%Y"),
        "{TIME}": datetime.now().strftime("%H:%M"),
        "{WEEKDAY}": datetime.now().strftime("%A"),
        "{GROUPNAME}": chat.title if chat else "",
        "{COUNT}": "0",
        "{RULES}": grupo_config.get('reglas', '') if grupo_config else ""
    }
    return variables

def procesar_mensaje(texto, variables):
    for key, value in variables.items():
        texto = texto.replace(key, str(value))
    return texto

# ==================== CREAR BOTONES ====================
def crear_botones(botones_config):
    if not botones_config:
        return None
    
    keyboard = []
    fila = []
    
    for b in botones_config:
        tipo = b.get('tipo', 'url')
        
        if tipo == 'url':
            fila.append(InlineKeyboardButton(b['texto'], url=b['url']))
        elif tipo == 'share':
            fila.append(InlineKeyboardButton(b['texto'], switch_inline_query="¡Mira este grupo!"))
        elif tipo == 'alert':
            fila.append(InlineKeyboardButton(b['texto'], callback_data=f"alert_{b.get('alert_text', '¡Mensaje!')}"))
        elif tipo == 'edit':
            fila.append(InlineKeyboardButton(b['texto'], callback_data=f"edit_{b.get('edit_text', 'Editado')}"))
        elif tipo == 'delete':
            fila.append(InlineKeyboardButton(b['texto'], callback_data="delete_msg"))
        elif tipo == 'callback':
            fila.append(InlineKeyboardButton(b['texto'], callback_data=f"custom_{b.get('callback_data', 'accion')}"))
        elif tipo == 'copy':
            fila.append(InlineKeyboardButton(b['texto'], callback_data=f"copy_{b.get('copy_text', 'Texto copiado')}"))
        
        if len(fila) >= 2:
            keyboard.append(fila)
            fila = []
    
    if fila:
        keyboard.append(fila)
    
    return InlineKeyboardMarkup(keyboard) if keyboard else None

# ==================== PROCESAR BOTONES CON && ====================
def procesar_botones_avanzado(texto):
    if not texto:
        return []
    
    botones = []
    lineas = texto.strip().split('\n')
    
    for linea in lineas:
        if not linea.strip():
            continue
        
        if ' && ' in linea:
            items = linea.split(' && ')
            for item in items:
                if ' - ' in item:
                    partes = item.strip().split(' - ', 1)
                    boton = crear_boton_desde_texto(partes[0].strip(), partes[1].strip())
                    if boton:
                        botones.append(boton)
        else:
            if ' - ' in linea:
                partes = linea.strip().split(' - ', 1)
                boton = crear_boton_desde_texto(partes[0].strip(), partes[1].strip())
                if boton:
                    botones.append(boton)
    
    return botones

def crear_boton_desde_texto(titulo, accion):
    if accion.startswith('popup:') or accion.startswith('alert:'):
        texto_popup = accion.replace('popup:', '').replace('alert:', '')
        return {"tipo": "alert", "texto": titulo, "alert_text": texto_popup}
    elif accion == 'rules':
        return {"tipo": "url", "texto": titulo, "url": "https://t.me/"}
    elif accion.startswith('share:'):
        texto_share = accion.replace('share:', '')
        return {"tipo": "share", "texto": titulo, "share_text": texto_share}
    elif accion.startswith('copy:'):
        texto_copy = accion.replace('copy:', '')
        return {"tipo": "copy", "texto": titulo, "copy_text": texto_copy}
    elif accion.startswith('t.me/') or accion.startswith('https://'):
        if not accion.startswith('http'):
            accion = 'https://' + accion
        return {"tipo": "url", "texto": titulo, "url": accion}
    else:
        return {"tipo": "url", "texto": titulo, "url": accion}

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
            "La configuración se realiza en el chat privado con el bot.\n"
            "📌 Abre el chat privado con el bot y usa /start.\n\n"
            "✅ Grupo registrado correctamente.",
            parse_mode="Markdown"
        )
        return
    
    config = cargar_config()
    grupos = config.get('grupos', {})
    
    if grupos:
        texto = "📋 *TUS GRUPOS CONFIGURADOS:*\n\n"
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
        await update.message.reply_text(
            "🤖 *BOT AVANZADO*\n\n"
            "No hay grupos configurados.\n"
            "Agrega el bot a un grupo y usa /start allí."
        )

# ==================== MENÚ PRINCIPAL ====================
async def menu_principal(update, context, edit=False, grupo_id=None):
    query = update.callback_query if edit else None
    
    if not grupo_id and query:
        grupo_id = query.message.chat_id
    elif not grupo_id and update.message:
        grupo_id = update.message.chat_id
    
    grupo_config = get_grupo_config(grupo_id)
    
    keyboard = [
        [InlineKeyboardButton("📝 Mensaje de Bienvenida", callback_data=f"menu_welcome_{grupo_id}")],
        [InlineKeyboardButton("👋 Mensaje de Despedida", callback_data=f"menu_goodbye_{grupo_id}")],
        [InlineKeyboardButton("📨 Mensajes Programados", callback_data=f"menu_mensajes_{grupo_id}")],
        [InlineKeyboardButton("📋 Reglas del Grupo", callback_data=f"menu_reglas_{grupo_id}")],
        [InlineKeyboardButton("✅ Auto-Aprobación", callback_data=f"menu_auto_{grupo_id}")],
        [InlineKeyboardButton("⏰ Tiempo Aprobación", callback_data=f"menu_tiempo_{grupo_id}")],
        [InlineKeyboardButton("🗑️ Eliminar Bienvenida", callback_data=f"menu_eliminar_{grupo_id}")],
        [InlineKeyboardButton("📌 Fijar Mensaje", callback_data=f"menu_fijar_{grupo_id}")],
        [InlineKeyboardButton("🛡️ Protección PV", callback_data=f"menu_proteccion_{grupo_id}")],
        [InlineKeyboardButton("👁️ Vista Previa", callback_data=f"menu_preview_{grupo_id}")],
        [InlineKeyboardButton("📊 Estado Grupo", callback_data=f"menu_status_{grupo_id}")],
        [InlineKeyboardButton("🔄 Resetear Grupo", callback_data=f"menu_reset_{grupo_id}")],
        [InlineKeyboardButton("📋 Listar Grupos", callback_data="menu_list_grupos")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    texto = (
        f"🤖 *CONFIGURACIÓN DEL GRUPO*\n"
        f"{'═' * 30}\n\n"
        f"📌 Grupo ID: `{grupo_id}`\n"
        f"✅ Auto-Aprobación: {'ON' if grupo_config.get('auto_aprobar', True) else 'OFF'}\n"
        f"⏰ Tiempo: {grupo_config.get('tiempo_aprobacion', 0)}s\n"
        f"🗑️ Eliminar bienvenida: {grupo_config.get('tiempo_eliminacion_bienvenida', 0)}s\n"
        f"📌 Fijar mensaje: {'✅' if grupo_config.get('fijar_mensaje', False) else '❌'}\n\n"
        f"Selecciona una opción:"
    )
    
    if edit and query:
        await query.edit_message_text(
            texto,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        await query.answer()
    else:
        await update.message.reply_text(
            texto,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

# ==================== MENÚ BIENVENIDA ====================
async def menu_welcome(update, context, grupo_id):
    query = update.callback_query
    grupo_config = get_grupo_config(grupo_id)
    
    keyboard = [
        [InlineKeyboardButton("📝 Texto ✔️", callback_data=f"welcome_text_{grupo_id}")],
        [InlineKeyboardButton("🖼️ Multimedia ❌", callback_data=f"welcome_media_{grupo_id}")],
        [InlineKeyboardButton("🔘 Teclado Inline ✔️", callback_data=f"welcome_buttons_{grupo_id}")],
        [InlineKeyboardButton("👁️ Vista previa completa", callback_data=f"welcome_preview_{grupo_id}")],
        [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Verificar estado
    texto = grupo_config.get('mensaje_bienvenida', 'No configurado')
    media = grupo_config.get('media_bienvenida')
    sticker = grupo_config.get('sticker_bienvenida')
    gif = grupo_config.get('gif_bienvenida')
    botones = grupo_config.get('botones_bienvenida', [])
    
    estado_texto = "✅" if texto and texto != 'No configurado' else "❌"
    estado_media = "✅" if media or sticker or gif else "❌"
    estado_botones = "✅" if botones else "❌"
    
    await query.edit_message_text(
        f"📝 *Mensaje de bienvenida*\n\n"
        f"Texto {estado_texto}\n"
        f"Multimedia {estado_media}\n"
        f"Teclado Inline {estado_botones}\n\n"
        f"- Usa los botones a continuación para elegir lo que deseas configurar",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await query.answer()

# ==================== MENÚ DESPEDIDA ====================
async def menu_goodbye(update, context, grupo_id):
    query = update.callback_query
    grupo_config = get_grupo_config(grupo_id)
    
    keyboard = [
        [InlineKeyboardButton("📝 Texto ✔️", callback_data=f"goodbye_text_{grupo_id}")],
        [InlineKeyboardButton("🖼️ Multimedia ❌", callback_data=f"goodbye_media_{grupo_id}")],
        [InlineKeyboardButton("🔘 Teclado Inline ✔️", callback_data=f"goodbye_buttons_{grupo_id}")],
        [InlineKeyboardButton("👁️ Vista previa completa", callback_data=f"goodbye_preview_{grupo_id}")],
        [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    texto = grupo_config.get('mensaje_despedida', 'No configurado')
    media = grupo_config.get('media_despedida')
    sticker = grupo_config.get('sticker_despedida')
    gif = grupo_config.get('gif_despedida')
    botones = grupo_config.get('botones_despedida', [])
    
    estado_texto = "✅" if texto and texto != 'No configurado' else "❌"
    estado_media = "✅" if media or sticker or gif else "❌"
    estado_botones = "✅" if botones else "❌"
    
    await query.edit_message_text(
        f"👋 *Mensaje de Despedida*\n\n"
        f"Texto {estado_texto}\n"
        f"Multimedia {estado_media}\n"
        f"Teclado Inline {estado_botones}\n\n"
        f"- Usa los botones a continuación para elegir lo que deseas configurar",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await query.answer()

# ==================== MENÚ MENSAJES PROGRAMADOS ====================
async def menu_mensajes(update, context, grupo_id):
    query = update.callback_query
    grupo_config = get_grupo_config(grupo_id)
    mensajes = grupo_config.get('mensajes_programados', [])
    
    texto = f"📨 *Mensajes Programados*\n\n"
    if mensajes:
        for i, msg in enumerate(mensajes, 1):
            seg = msg.get('intervalo', 3600)
            texto += f"{i}. Cada {seg/60:.0f}min: {msg.get('mensaje', '')[:30]}...\n"
    else:
        texto += "No hay mensajes programados.\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Agregar Mensaje", callback_data=f"mensaje_add_{grupo_id}")],
        [InlineKeyboardButton("🗑️ Eliminar Mensaje", callback_data=f"mensaje_del_{grupo_id}")],
        [InlineKeyboardButton("📋 Listar Mensajes", callback_data=f"mensaje_list_{grupo_id}")],
        [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        texto,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await query.answer()

# ==================== SUBMENÚ AGREGAR MENSAJE ====================
async def mensaje_add(update, context, grupo_id):
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton("📝 Texto", callback_data=f"mensaje_add_text_{grupo_id}")],
        [InlineKeyboardButton("🖼️ Multimedia", callback_data=f"mensaje_add_media_{grupo_id}")],
        [InlineKeyboardButton("🔘 Botones", callback_data=f"mensaje_add_buttons_{grupo_id}")],
        [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_mensajes_{grupo_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📨 *Agregar Mensaje Programado*\n\n"
        "Selecciona qué tipo de mensaje deseas agregar:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await query.answer()

# ==================== SUBMENÚ TEXTO ====================
async def submenu_texto(update, context, grupo_id, tipo):
    query = update.callback_query
    
    nombre = {
        "welcome": "Bienvenida",
        "goodbye": "Despedida",
        "reingreso": "Reingreso"
    }.get(tipo, "Mensaje")
    
    await query.edit_message_text(
        f"✏️ *Editar Mensaje de {nombre}*\n\n"
        "Envía el nuevo mensaje.\n\n"
        "Variables disponibles:\n"
        "• `{NAME}` - Nombre del usuario\n"
        "• `{MENTION}` - Mención al usuario\n"
        "• `{USERNAME}` - @username\n"
        "• `{GROUPNAME}` - Nombre del grupo\n"
        "• `{RULES}` - Reglas del grupo\n"
        "• `{DATE}` - Fecha actual\n"
        "• `{TIME}` - Hora actual\n\n"
        "Ejemplo: `¡Bienvenido {MENTION}!`\n\n"
        "Para cancelar: /cancelar",
        parse_mode="Markdown"
    )
    context.user_data['esperando'] = f'texto_{tipo}'
    context.user_data['grupo_id'] = grupo_id
    await query.answer()

# ==================== SUBMENÚ MULTIMEDIA ====================
async def submenu_media(update, context, grupo_id, tipo):
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton("🖼️ Foto", callback_data=f"media_foto_{tipo}_{grupo_id}")],
        [InlineKeyboardButton("🎬 Video", callback_data=f"media_video_{tipo}_{grupo_id}")],
        [InlineKeyboardButton("🔵 GIF", callback_data=f"media_gif_{tipo}_{grupo_id}")],
        [InlineKeyboardButton("⭐ Sticker", callback_data=f"media_sticker_{tipo}_{grupo_id}")],
        [InlineKeyboardButton("🗑️ Eliminar", callback_data=f"media_delete_{tipo}_{grupo_id}")],
        [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_{tipo}_{grupo_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Verificar qué media tiene
    grupo_config = get_grupo_config(grupo_id)
    media_map = {
        'bienvenida': grupo_config.get('media_bienvenida'),
        'reingreso': grupo_config.get('media_reingreso'),
        'despedida': grupo_config.get('media_despedida')
    }
    sticker_map = {
        'bienvenida': grupo_config.get('sticker_bienvenida'),
        'reingreso': grupo_config.get('sticker_reingreso'),
        'despedida': grupo_config.get('sticker_despedida')
    }
    gif_map = {
        'bienvenida': grupo_config.get('gif_bienvenida'),
        'reingreso': grupo_config.get('gif_reingreso'),
        'despedida': grupo_config.get('gif_despedida')
    }
    
    estado = []
    if media_map.get(tipo):
        estado.append("📸 Foto")
    if sticker_map.get(tipo):
        estado.append("⭐ Sticker")
    if gif_map.get(tipo):
        estado.append("🔵 GIF")
    
    estado_texto = "✅ " + ", ".join(estado) if estado else "❌ No hay multimedia"
    
    await query.edit_message_text(
        f"🖼️ *Multimedia - {tipo.upper()}*\n\n"
        f"*Estado:* {estado_texto}\n\n"
        f"Selecciona el tipo de multimedia que deseas agregar.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await query.answer()

# ==================== SUBMENÚ BOTONES ====================
async def submenu_botones(update, context, grupo_id, tipo):
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton("➕ Agregar Botones", callback_data=f"botones_add_{tipo}_{grupo_id}")],
        [InlineKeyboardButton("⬆️ Mover Arriba", callback_data=f"botones_up_{tipo}_{grupo_id}")],
        [InlineKeyboardButton("⬇️ Mover Abajo", callback_data=f"botones_down_{tipo}_{grupo_id}")],
        [InlineKeyboardButton("🗑️ Eliminar Todos", callback_data=f"botones_clear_{tipo}_{grupo_id}")],
        [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_{tipo}_{grupo_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    grupo_config = get_grupo_config(grupo_id)
    botones_key = f"botones_{tipo}"
    botones = grupo_config.get(botones_key, [])
    
    texto = f"🔘 *Teclado Inline - {tipo.upper()}*\n\n"
    if botones:
        for i, b in enumerate(botones, 1):
            tipo_btn = b.get('tipo', 'url')
            emoji = {'url': '🔗', 'share': '📤', 'alert': '⚠️', 'edit': '✏️', 'delete': '🗑️', 'callback': '⚡', 'copy': '📋'}.get(tipo_btn, '📌')
            texto += f"{i}. {emoji} {b['texto']} ({tipo_btn})\n"
    else:
        texto += "No hay botones configurados.\n"
    
    await query.edit_message_text(
        texto,
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
    
    # ========== ACCIONES RÁPIDAS ==========
    if data.startswith("alert_"):
        alert_text = data.replace('alert_', '')
        await query.answer(alert_text, show_alert=True)
        return
    
    if data.startswith("copy_"):
        copy_text = data.replace('copy_', '')
        await query.answer(f"📋 Texto copiado:\n{copy_text}", show_alert=True)
        return
    
    if data.startswith("edit_"):
        edit_text = data.replace('edit_', '')
        await query.edit_message_text(
            f"✏️ *Mensaje editado:*\n\n{edit_text}",
            parse_mode="Markdown"
        )
        return
    
    if data == "delete_msg":
        try:
            await query.delete_message()
        except:
            pass
        return
    
    if data.startswith("custom_"):
        custom_data = data.replace('custom_', '')
        await query.answer(f"⚡ Acción: {custom_data}")
        return
    
    # ========== LISTAR GRUPOS ==========
    if data == "menu_list_grupos":
        await listar_grupos(update, context)
        return
    
    if data.startswith("menu_grupo_"):
        grupo_id = data.replace("menu_grupo_", "")
        await menu_principal(update, context, edit=True, grupo_id=int(grupo_id))
        return
    
    # ========== EXTRAER GRUPO ID ==========
    parts = data.split('_')
    if len(parts) < 3:
        return
    
    grupo_id = parts[-1]
    try:
        grupo_id = int(grupo_id)
    except:
        return
    
    grupo_config = get_grupo_config(grupo_id)
    config = cargar_config()
    
    # ========== MENÚ BIENVENIDA ==========
    if data.startswith("menu_welcome_"):
        await menu_welcome(update, context, grupo_id)
        return
    
    # ========== MENÚ DESPEDIDA ==========
    if data.startswith("menu_goodbye_"):
        await menu_goodbye(update, context, grupo_id)
        return
    
    # ========== MENÚ MENSAJES PROGRAMADOS ==========
    if data.startswith("menu_mensajes_"):
        await menu_mensajes(update, context, grupo_id)
        return
    
    # ========== AGREGAR MENSAJE PROGRAMADO ==========
    if data.startswith("mensaje_add_"):
        await mensaje_add(update, context, grupo_id)
        return
    
    if data.startswith("mensaje_add_text_"):
        await query.edit_message_text(
            "📝 *Agregar Mensaje de Texto*\n\n"
            "Envía en formato:\n"
            "`segundos|mensaje`\n\n"
            "Ejemplo: `120|¡Hola {NAME}!`\n\n"
            "Mínimo 60 segundos\n\nPara cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'addmsg_text'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("mensaje_add_media_"):
        await query.edit_message_text(
            "🖼️ *Agregar Mensaje con Multimedia*\n\n"
            "Envía en formato:\n"
            "`segundos`\n\n"
            "Luego envía la foto, video, GIF o sticker.\n\n"
            "Ejemplo: `120`\n\n"
            "Mínimo 60 segundos\n\nPara cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'addmsg_media'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("mensaje_add_buttons_"):
        await query.edit_message_text(
            "🔘 *Agregar Botones a Mensaje Programado*\n\n"
            "Envía los botones en formato:\n"
            "`Título - t.me/enlace`\n"
            "`Título1 - link1 && Título2 - link2`\n\n"
            "Ejemplo:\n"
            "`📢 Canal - t.me/mi_canal && 📋 Reglas - t.me/reglas`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'addmsg_buttons'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("mensaje_del_"):
        await query.edit_message_text(
            "🗑️ *Eliminar Mensaje Programado*\n\n"
            "Envía el número del mensaje:\n`1`\n\nPara cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'delmsg'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("mensaje_list_"):
        mensajes = grupo_config.get('mensajes_programados', [])
        if not mensajes:
            await query.edit_message_text("📨 No hay mensajes programados.")
            return
        
        texto = "📨 *Mensajes Programados:*\n\n"
        for i, msg in enumerate(mensajes, 1):
            seg = msg.get('intervalo', 3600)
            texto += f"{i}. Cada {seg/60:.0f}min: {msg.get('mensaje', '')[:30]}...\n"
            if msg.get('media'):
                texto += "   🖼️ Con media\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_mensajes_{grupo_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
        return
    
    # ========== TEXTO ==========
    if data.startswith("welcome_text_"):
        await submenu_texto(update, context, grupo_id, "welcome")
        return
    
    if data.startswith("goodbye_text_"):
        await submenu_texto(update, context, grupo_id, "goodbye")
        return
    
    if data.startswith("reingreso_text_"):
        await submenu_texto(update, context, grupo_id, "reingreso")
        return
    
    # ========== MULTIMEDIA ==========
    if data.startswith("welcome_media_"):
        await submenu_media(update, context, grupo_id, "bienvenida")
        return
    
    if data.startswith("goodbye_media_"):
        await submenu_media(update, context, grupo_id, "despedida")
        return
    
    # ========== BOTONES ==========
    if data.startswith("welcome_buttons_"):
        await submenu_botones(update, context, grupo_id, "bienvenida")
        return
    
    if data.startswith("goodbye_buttons_"):
        await submenu_botones(update, context, grupo_id, "despedida")
        return
    
    if data.startswith("reingreso_buttons_"):
        await submenu_botones(update, context, grupo_id, "reingreso")
        return
    
    # ========== AGREGAR BOTONES ==========
    if data.startswith("botones_add_"):
        tipo = data.split('_')[2]
        await query.edit_message_text(
            "✏️ *Agregar Botones*\n\n"
            "Envía los botones en formato:\n"
            "`Título - t.me/enlace`\n"
            "`Título1 - link1 && Título2 - link2`\n\n"
            "Ejemplo:\n"
            "`📢 Canal - t.me/mi_canal && 📋 Reglas - t.me/reglas`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = f'botones_{tipo}'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("botones_clear_"):
        tipo = data.split('_')[2]
        key = f"botones_{tipo}"
        grupo_config[key] = []
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text(f"✅ Botones de {tipo} eliminados")
        await submenu_botones(update, context, grupo_id, tipo)
        return
    
    if data.startswith("botones_up_"):
        tipo = data.split('_')[2]
        await query.edit_message_text(
            f"⬆️ *Mover Botón Arriba*\n\n"
            f"Envía el número del botón a mover:\n`1`\n\nPara cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = f'botones_up_{tipo}'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("botones_down_"):
        tipo = data.split('_')[2]
        await query.edit_message_text(
            f"⬇️ *Mover Botón Abajo*\n\n"
            f"Envía el número del botón a mover:\n`1`\n\nPara cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = f'botones_down_{tipo}'
        context.user_data['grupo_id'] = grupo_id
        return
    
    # ========== MULTIMEDIA - FOTO/VIDEO/GIF/STICKER ==========
    if data.startswith("media_foto_"):
        tipo = data.split('_')[2]
        await query.edit_message_text(
            f"📸 *Agregar Foto para {tipo.upper()}*\n\n"
            "Envía la foto que deseas usar.\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = f'media_foto_{tipo}'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("media_video_"):
        tipo = data.split('_')[2]
        await query.edit_message_text(
            f"🎬 *Agregar Video para {tipo.upper()}*\n\n"
            "Envía el video que deseas usar.\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = f'media_video_{tipo}'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("media_gif_"):
        tipo = data.split('_')[2]
        await query.edit_message_text(
            f"🔵 *Agregar GIF para {tipo.upper()}*\n\n"
            "Envía el GIF que deseas usar (como archivo o desde el teclado GIF).\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = f'media_gif_{tipo}'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("media_sticker_"):
        tipo = data.split('_')[2]
        await query.edit_message_text(
            f"⭐ *Agregar Sticker para {tipo.upper()}*\n\n"
            "Envía el sticker que deseas usar.\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = f'media_sticker_{tipo}'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("media_delete_"):
        tipo = data.split('_')[2]
        grupo_config[f'media_{tipo}'] = None
        grupo_config[f'sticker_{tipo}'] = None
        grupo_config[f'gif_{tipo}'] = None
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text(f"✅ Multimedia de {tipo} eliminada")
        await submenu_media(update, context, grupo_id, tipo)
        return
    
    # ========== VISTA PREVIA ==========
    if data.startswith("welcome_preview_"):
        await preview_grupo(update, context, grupo_id, "bienvenida")
        await query.delete_message()
        return
    
    if data.startswith("goodbye_preview_"):
        await preview_grupo(update, context, grupo_id, "despedida")
        await query.delete_message()
        return
    
    # ========== REGLAS ==========
    if data.startswith("menu_reglas_"):
        await query.edit_message_text(
            "📋 *Configurar Reglas del Grupo*\n\n"
            "Envía el texto de las reglas.\n\n"
            "Variables disponibles:\n"
            "• `{NAME}` - Nombre del usuario\n"
            "• `{MENTION}` - Mención al usuario\n"
            "• `{GROUPNAME}` - Nombre del grupo\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'reglas'
        context.user_data['grupo_id'] = grupo_id
        return
    
    # ========== FIJAR MENSAJE ==========
    if data.startswith("menu_fijar_"):
        fijar = grupo_config.get('fijar_mensaje', False)
        keyboard = [
            [InlineKeyboardButton("✅ Activar" if not fijar else "✅ Ya Activado", callback_data=f"fijar_on_{grupo_id}")],
            [InlineKeyboardButton("❌ Desactivar" if fijar else "❌ Ya Desactivado", callback_data=f"fijar_off_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        estado = "✅ Activado" if fijar else "❌ Desactivado"
        await query.edit_message_text(
            f"📌 *FIJAR MENSAJE*\n\nEstado: {estado}\n\nCuando está activado, el mensaje de bienvenida se fija en el chat del usuario.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("fijar_on_"):
        grupo_config['fijar_mensaje'] = True
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("✅ Fijar mensaje ACTIVADO")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    if data.startswith("fijar_off_"):
        grupo_config['fijar_mensaje'] = False
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("❌ Fijar mensaje DESACTIVADO")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    # ========== ELIMINAR BIENVENIDA ==========
    if data.startswith("menu_eliminar_"):
        keyboard = [
            [InlineKeyboardButton("❌ Desactivar (0s)", callback_data=f"elim_0_{grupo_id}")],
            [InlineKeyboardButton("⏰ 30s", callback_data=f"elim_30_{grupo_id}")],
            [InlineKeyboardButton("⏰ 60s", callback_data=f"elim_60_{grupo_id}")],
            [InlineKeyboardButton("⏰ 120s", callback_data=f"elim_120_{grupo_id}")],
            [InlineKeyboardButton("⏰ 300s", callback_data=f"elim_300_{grupo_id}")],
            [InlineKeyboardButton("⏰ 600s", callback_data=f"elim_600_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        tiempo = grupo_config.get('tiempo_eliminacion_bienvenida', 0)
        await query.edit_message_text(
            f"🗑️ *ELIMINAR BIENVENIDA*\n\nActual: {tiempo}s\n\n0 = No eliminar",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("elim_"):
        segundos = int(data.split('_')[1])
        grupo_config['tiempo_eliminacion_bienvenida'] = segundos
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text(f"✅ Bienvenida se eliminará después de {segundos}s")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    # ========== AUTO-APROBACIÓN ==========
    if data.startswith("menu_auto_"):
        keyboard = [
            [InlineKeyboardButton("✅ Activar", callback_data=f"auto_on_{grupo_id}")],
            [InlineKeyboardButton("❌ Desactivar", callback_data=f"auto_off_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        estado = "ON" if grupo_config.get('auto_aprobar', True) else "OFF"
        await query.edit_message_text(
            f"✅ *AUTO-APROBACIÓN*\n\nEstado: {estado}",
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
    if data.startswith("menu_tiempo_"):
        keyboard = [
            [InlineKeyboardButton("⚡ Inmediata", callback_data=f"t_0_{grupo_id}")],
            [InlineKeyboardButton("⏰ 30s", callback_data=f"t_30_{grupo_id}")],
            [InlineKeyboardButton("⏰ 60s", callback_data=f"t_60_{grupo_id}")],
            [InlineKeyboardButton("⏰ 120s", callback_data=f"t_120_{grupo_id}")],
            [InlineKeyboardButton("⏰ 300s", callback_data=f"t_300_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        tiempo = grupo_config.get('tiempo_aprobacion', 0)
        await query.edit_message_text(
            f"⏰ *TIEMPO APROBACIÓN*\n\nActual: {tiempo}s",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("t_"):
        segundos = int(data.split('_')[1])
        grupo_config['tiempo_aprobacion'] = segundos
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text(f"✅ Tiempo: {segundos}s")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    # ========== PROTECCIÓN ==========
    if data.startswith("menu_proteccion_"):
        keyboard = [
            [InlineKeyboardButton("🔒 Activar Protección", callback_data=f"proteger_on_{grupo_id}")],
            [InlineKeyboardButton("🔓 Desactivar Protección", callback_data=f"proteger_off_{grupo_id}")],
            [InlineKeyboardButton("🗑️ Borrar PV: ON", callback_data=f"borrar_on_{grupo_id}")],
            [InlineKeyboardButton("🗑️ Borrar PV: OFF", callback_data=f"borrar_off_{grupo_id}")],
            [InlineKeyboardButton("⏰ Tiempo Borrado", callback_data=f"borrar_tiempo_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"🛡️ *PROTECCIÓN*\n\n• Protección: {'ON' if config.get('proteger_mensajes', True) else 'OFF'}\n• Borrado PV: {'ON' if config.get('borrar_mensajes_pv', True) else 'OFF'}\n• Tiempo: {config.get('tiempo_borrado_pv', 60)}s",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("proteger_on_"):
        config['proteger_mensajes'] = True
        guardar_config(config)
        await query.edit_message_text("✅ Protección ACTIVADA")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    if data.startswith("proteger_off_"):
        config['proteger_mensajes'] = False
        guardar_config(config)
        await query.edit_message_text("❌ Protección DESACTIVADA")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    if data.startswith("borrar_on_"):
        config['borrar_mensajes_pv'] = True
        guardar_config(config)
        await query.edit_message_text("✅ Borrado PV ACTIVADO")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    if data.startswith("borrar_off_"):
        config['borrar_mensajes_pv'] = False
        guardar_config(config)
        await query.edit_message_text("❌ Borrado PV DESACTIVADO")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    if data.startswith("borrar_tiempo_"):
        keyboard = [
            [InlineKeyboardButton("30s", callback_data=f"bt_30_{grupo_id}")],
            [InlineKeyboardButton("60s", callback_data=f"bt_60_{grupo_id}")],
            [InlineKeyboardButton("120s", callback_data=f"bt_120_{grupo_id}")],
            [InlineKeyboardButton("300s", callback_data=f"bt_300_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_proteccion_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("⏰ *Tiempo de borrado:*")
        return
    
    if data.startswith("bt_"):
        segundos = int(data.split('_')[1])
        config['tiempo_borrado_pv'] = segundos
        guardar_config(config)
        await query.edit_message_text(f"✅ Tiempo: {segundos}s")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    # ========== STATUS ==========
    if data.startswith("menu_status_"):
        registro = cargar_registro()
        usuarios_grupo = [u for u in registro.get('usuarios', {}).values() if u.get('grupo') == str(grupo_id)]
        
        texto = (
            f"📊 *ESTADO*\n\n"
            f"👥 Usuarios: {len(usuarios_grupo)}\n"
            f"🔘 Botones Bienvenida: {len(grupo_config.get('botones_bienvenida', []))}\n"
            f"🔘 Botones Despedida: {len(grupo_config.get('botones_despedida', []))}\n"
            f"🔘 Botones Repetidos: {len(grupo_config.get('botones_repetidos', []))}\n"
            f"📨 Programados: {len(grupo_config.get('mensajes_programados', []))}\n"
            f"🖼️ Media: {'✅' if grupo_config.get('media_bienvenida') else '❌'}"
        )
        keyboard = [[InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
        return
    
    # ========== RESET ==========
    if data.startswith("menu_reset_"):
        keyboard = [
            [InlineKeyboardButton("✅ Sí", callback_data=f"reset_confirm_{grupo_id}")],
            [InlineKeyboardButton("❌ No", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"⚠️ *¿RESETEAR Grupo {grupo_id}?*\nNo se puede deshacer.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("reset_confirm_"):
        config = cargar_config()
        config['grupos'][str(grupo_id)] = {
            "mensaje_bienvenida": config_default['mensaje_bienvenida'],
            "mensaje_reingreso": config_default['mensaje_reingreso'],
            "mensaje_despedida": config_default['mensaje_despedida'],
            "botones_bienvenida": [],
            "botones_despedida": [],
            "botones_repetidos": [],
            "media_bienvenida": None,
            "media_reingreso": None,
            "media_despedida": None,
            "sticker_bienvenida": None,
            "sticker_reingreso": None,
            "sticker_despedida": None,
            "gif_bienvenida": None,
            "gif_reingreso": None,
            "gif_despedida": None,
            "auto_aprobar": True,
            "tiempo_aprobacion": 0,
            "mensajes_programados": [],
            "tiempo_eliminacion_bienvenida": 0,
            "mensajes_activos": {},
            "fijar_mensaje": False,
            "reglas": ""
        }
        guardar_config(config)
        await query.edit_message_text(f"✅ Grupo {grupo_id} reseteado")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    # ========== ATRÁS ==========
    if data.startswith("menu_back_"):
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return

# ==================== PREVIEW ====================
async def preview_grupo(update, context, grupo_id, tipo):
    grupo_config = get_grupo_config(grupo_id)
    
    if tipo == "bienvenida":
        mensaje = grupo_config.get('mensaje_bienvenida', 'No configurado')
        media = grupo_config.get('media_bienvenida')
        sticker = grupo_config.get('sticker_bienvenida')
        gif = grupo_config.get('gif_bienvenida')
        botones = grupo_config.get('botones_bienvenida', [])
    else:
        mensaje = grupo_config.get('mensaje_despedida', 'No configurado')
        media = grupo_config.get('media_despedida')
        sticker = grupo_config.get('sticker_despedida')
        gif = grupo_config.get('gif_despedida')
        botones = grupo_config.get('botones_despedida', [])
    
    variables = {
        "{ID}": "123456789",
        "{NAME}": "Usuario",
        "{SURNAME}": "Prueba",
        "{NAMESURNAME}": "Usuario Prueba",
        "{USERNAME}": "@usuario",
        "{MENTION}": '<a href="tg://user?id=123456789">Usuario</a>',
        "{LANG}": "es",
        "{DATE}": datetime.now().strftime("%d/%m/%Y"),
        "{TIME}": datetime.now().strftime("%H:%M"),
        "{WEEKDAY}": datetime.now().strftime("%A"),
        "{GROUPNAME}": "Grupo de Prueba",
        "{RULES}": "Reglas del grupo",
        "{COUNT}": "100"
    }
    
    mensaje_prueba = procesar_mensaje(mensaje, variables)
    reply_markup = crear_botones(botones)
    
    try:
        if media and media.get('file_id'):
            if media.get('tipo') == 'foto':
                await update.callback_query.message.reply_photo(
                    photo=media.get('file_id'),
                    caption=f"👁️ *Vista previa:*\n\n{mensaje_prueba}",
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            elif media.get('tipo') == 'video':
                await update.callback_query.message.reply_video(
                    video=media.get('file_id'),
                    caption=f"👁️ *Vista previa:*\n\n{mensaje_prueba}",
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
        elif sticker:
            await update.callback_query.message.reply_sticker(
                sticker=sticker,
                reply_markup=reply_markup
            )
            await update.callback_query.message.reply_text(
                f"👁️ *Vista previa:*\n\n{mensaje_prueba}",
                parse_mode="HTML"
            )
        elif gif:
            await update.callback_query.message.reply_animation(
                animation=gif,
                caption=f"👁️ *Vista previa:*\n\n{mensaje_prueba}",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        else:
            await update.callback_query.message.reply_text(
                f"👁️ *Vista previa:*\n\n{mensaje_prueba}",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
    except Exception as e:
        await update.callback_query.message.reply_text(
            f"❌ Error al mostrar vista previa: {str(e)}"
        )

# ==================== LISTAR GRUPOS ====================
async def listar_grupos(update, context):
    query = update.callback_query
    config = cargar_config()
    grupos = config.get('grupos', {})
    
    if not grupos:
        await query.edit_message_text("📋 No hay grupos configurados.")
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
        await update.message.reply_text("❌ Error: no hay grupo configurado.")
        return
    
    grupo_config = get_grupo_config(grupo_id)
    
    # ========== TEXTO ==========
    if estado.startswith('texto_'):
        tipo = estado.replace('texto_', '')
        if tipo == 'welcome':
            grupo_config['mensaje_bienvenida'] = update.message.text
        elif tipo == 'goodbye':
            grupo_config['mensaje_despedida'] = update.message.text
        elif tipo == 'reingreso':
            grupo_config['mensaje_reingreso'] = update.message.text
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text(f"✅ Mensaje de {tipo} actualizado.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return
    
    # ========== REGLAS ==========
    if estado == 'reglas':
        grupo_config['reglas'] = update.message.text
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text("✅ Reglas guardadas correctamente.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return
    
    # ========== BOTONES ==========
    if estado.startswith('botones_'):
        tipo = estado.replace('botones_', '')
        key = f"botones_{tipo}"
        
        if key not in grupo_config:
            grupo_config[key] = []
        
        botones_nuevos = procesar_botones_avanzado(update.message.text)
        
        if botones_nuevos:
            grupo_config[key].extend(botones_nuevos)
            guardar_grupo_config(grupo_id, grupo_config)
            await update.message.reply_text(f"✅ {len(botones_nuevos)} botones agregados")
        else:
            await update.message.reply_text("❌ Formato incorrecto. Usa: `Título - t.me/enlace`")
        
        context.user_data.clear()
        await submenu_botones(update, context, grupo_id, tipo)
        return
    
    if estado.startswith('botones_up_'):
        tipo = estado.replace('botones_up_', '')
        key = f"botones_{tipo}"
        try:
            num = int(update.message.text) - 1
            if 0 <= num < len(grupo_config.get(key, [])) and num > 0:
                grupo_config[key][num], grupo_config[key][num-1] = grupo_config[key][num-1], grupo_config[key][num]
                guardar_grupo_config(grupo_id, grupo_config)
                await update.message.reply_text(f"✅ Botón {num+1} movido hacia arriba")
            else:
                await update.message.reply_text("❌ Número inválido")
        except:
            await update.message.reply_text("❌ Envía un número válido")
        context.user_data.clear()
        await submenu_botones(update, context, grupo_id, tipo)
        return
    
    if estado.startswith('botones_down_'):
        tipo = estado.replace('botones_down_', '')
        key = f"botones_{tipo}"
        try:
            num = int(update.message.text) - 1
            if 0 <= num < len(grupo_config.get(key, [])) and num < len(grupo_config.get(key, [])) - 1:
                grupo_config[key][num], grupo_config[key][num+1] = grupo_config[key][num+1], grupo_config[key][num]
                guardar_grupo_config(grupo_id, grupo_config)
                await update.message.reply_text(f"✅ Botón {num+1} movido hacia abajo")
            else:
                await update.message.reply_text("❌ Número inválido")
        except:
            await update.message.reply_text("❌ Envía un número válido")
        context.user_data.clear()
        await submenu_botones(update, context, grupo_id, tipo)
        return
    
    # ========== MULTIMEDIA ==========
    if estado.startswith('media_foto_'):
        tipo = estado.replace('media_foto_', '')
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            grupo_config[f'media_{tipo}'] = {"tipo": "foto", "file_id": file_id}
            guardar_grupo_config(grupo_id, grupo_config)
            await update.message.reply_text(f"✅ Foto guardada para {tipo}")
        else:
            await update.message.reply_text("❌ Envía una foto.")
            return
        context.user_data.clear()
        await submenu_media(update, context, grupo_id, tipo)
        return
    
    if estado.startswith('media_video_'):
        tipo = estado.replace('media_video_', '')
        if update.message.video:
            file_id = update.message.video.file_id
            grupo_config[f'media_{tipo}'] = {"tipo": "video", "file_id": file_id}
            guardar_grupo_config(grupo_id, grupo_config)
            await update.message.reply_text(f"✅ Video guardado para {tipo}")
        else:
            await update.message.reply_text("❌ Envía un video.")
            return
        context.user_data.clear()
        await submenu_media(update, context, grupo_id, tipo)
        return
    
    if estado.startswith('media_gif_'):
        tipo = estado.replace('media_gif_', '')
        if update.message.animation or update.message.document:
            if update.message.animation:
                file_id = update.message.animation.file_id
            else:
                file_id = update.message.document.file_id
            grupo_config[f'gif_{tipo}'] = file_id
            guardar_grupo_config(grupo_id, grupo_config)
            await update.message.reply_text(f"✅ GIF guardado para {tipo}")
        else:
            await update.message.reply_text("❌ Envía un GIF.")
            return
        context.user_data.clear()
        await submenu_media(update, context, grupo_id, tipo)
        return
    
    if estado.startswith('media_sticker_'):
        tipo = estado.replace('media_sticker_', '')
        if update.message.sticker:
            file_id = update.message.sticker.file_id
            grupo_config[f'sticker_{tipo}'] = file_id
            guardar_grupo_config(grupo_id, grupo_config)
            await update.message.reply_text(f"✅ Sticker guardado para {tipo}")
        else:
            await update.message.reply_text("❌ Envía un sticker.")
            return
        context.user_data.clear()
        await submenu_media(update, context, grupo_id, tipo)
        return
    
    # ========== MENSAJES PROGRAMADOS ==========
    if estado == 'addmsg_text':
        try:
            partes = update.message.text.split('|', 1)
            if len(partes) != 2:
                await update.message.reply_text("❌ Formato: `segundos|mensaje`")
                return
            
            segundos = float(partes[0])
            if segundos < 60:
                await update.message.reply_text("⚠️ Mínimo 60 segundos")
                return
            
            mensaje = partes[1]
            
            if 'mensajes_programados' not in grupo_config:
                grupo_config['mensajes_programados'] = []
            
            grupo_config['mensajes_programados'].append({
                "intervalo": segundos,
                "mensaje": mensaje,
                "media": None,
                "botones": []
            })
            guardar_grupo_config(grupo_id, grupo_config)
            
            # Programar en job_queue
            if context.application.job_queue:
                context.application.job_queue.run_repeating(
                    enviar_mensaje_programado,
                    interval=segundos,
                    first=5,
                    name=f"msg_{grupo_id}_{len(grupo_config['mensajes_programados'])}",
                    chat_id=grupo_id,
                    user_id=grupo_id
                )
            
            await update.message.reply_text(f"✅ Mensaje programado cada {segundos/60:.0f} minutos")
            context.user_data.clear()
            await menu_mensajes(update, context, grupo_id)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
        return
    
    if estado == 'addmsg_media':
        try:
            segundos = float(update.message.text)
            if segundos < 60:
                await update.message.reply_text("⚠️ Mínimo 60 segundos")
                return
            
            context.user_data['esperando_media'] = segundos
            await update.message.reply_text(f"📤 Envía la foto, video, GIF o sticker para cada {segundos/60:.0f} min")
            context.user_data['esperando'] = 'addmsg_media_file'
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
        return
    
    if estado == 'addmsg_media_file':
        try:
            segundos = context.user_data.get('esperando_media', 0)
            if not segundos:
                return
            
            if 'mensajes_programados' not in grupo_config:
                grupo_config['mensajes_programados'] = []
            
            media_data = None
            
            if update.message.photo:
                file_id = update.message.photo[-1].file_id
                media_data = {"tipo": "foto", "file_id": file_id}
            elif update.message.video:
                file_id = update.message.video.file_id
                media_data = {"tipo": "video", "file_id": file_id}
            elif update.message.animation or update.message.document:
                if update.message.animation:
                    file_id = update.message.animation.file_id
                else:
                    file_id = update.message.document.file_id
                media_data = {"tipo": "gif", "file_id": file_id}
            elif update.message.sticker:
                file_id = update.message.sticker.file_id
                media_data = {"tipo": "sticker", "file_id": file_id}
            else:
                await update.message.reply_text("❌ Envía una foto, video, GIF o sticker.")
                return
            
            grupo_config['mensajes_programados'].append({
                "intervalo": segundos,
                "mensaje": "¡Hola {NAME}! Recuerda visitar el grupo 🎉",
                "media": media_data,
                "botones": []
            })
            guardar_grupo_config(grupo_id, grupo_config)
            
            if context.application.job_queue:
                context.application.job_queue.run_repeating(
                    enviar_mensaje_programado,
                    interval=segundos,
                    first=5,
                    name=f"msg_{grupo_id}_{len(grupo_config['mensajes_programados'])}",
                    chat_id=grupo_id,
                    user_id=grupo_id
                )
            
            await update.message.reply_text(f"✅ Mensaje con multimedia programado cada {segundos/60:.0f} min")
            context.user_data.clear()
            await menu_mensajes(update, context, grupo_id)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
        return
    
    if estado == 'addmsg_buttons':
        try:
            botones_nuevos = procesar_botones_avanzado(update.message.text)
            
            if not botones_nuevos:
                await update.message.reply_text("❌ Formato incorrecto. Usa: `Título - t.me/enlace`")
                return
            
            # Agregar botones al último mensaje programado
            if 'mensajes_programados' not in grupo_config or not grupo_config['mensajes_programados']:
                await update.message.reply_text("❌ Primero agrega un mensaje antes de agregar botones.")
                return
            
            ultimo = grupo_config['mensajes_programados'][-1]
            if 'botones' not in ultimo:
                ultimo['botones'] = []
            ultimo['botones'].extend(botones_nuevos)
            guardar_grupo_config(grupo_id, grupo_config)
            
            await update.message.reply_text(f"✅ {len(botones_nuevos)} botones agregados al mensaje programado")
            context.user_data.clear()
            await menu_mensajes(update, context, grupo_id)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
        return
    
    if estado == 'delmsg':
        try:
            num = int(update.message.text) - 1
            mensajes = grupo_config.get('mensajes_programados', [])
            
            if 0 <= num < len(mensajes):
                grupo_config['mensajes_programados'].pop(num)
                guardar_grupo_config(grupo_id, grupo_config)
                await update.message.reply_text("✅ Mensaje eliminado")
            else:
                await update.message.reply_text("❌ Número inválido")
            context.user_data.clear()
            await menu_mensajes(update, context, grupo_id)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
        return

# ==================== MENSAJES PROGRAMADOS ====================
async def enviar_mensaje_programado(context):
    try:
        job = context.job
        if not job or not job.name:
            return
        
        parts = job.name.split('_')
        if len(parts) < 2:
            return
        grupo_id = int(parts[1])
        
        grupo_config = get_grupo_config(grupo_id)
        config_global = cargar_config()
        
        try:
            chat_members = await context.bot.get_chat_administrators(grupo_id)
            user_ids = [m.user.id for m in chat_members]
        except:
            return
        
        if not user_ids:
            return
        
        try:
            chat = await context.bot.get_chat(grupo_id)
        except:
            chat = None
        
        for msg_config in grupo_config.get('mensajes_programados', []):
            mensaje = msg_config.get('mensaje', '')
            media = msg_config.get('media')
            botones = msg_config.get('botones', [])
            
            for user_id in user_ids:
                try:
                    try:
                        user = await context.bot.get_chat(user_id)
                    except:
                        continue
                    
                    variables = obtener_variables(user, chat, grupo_config)
                    texto = procesar_mensaje(mensaje, variables)
                    
                    reply_markup = crear_botones(botones)
                    
                    if media and media.get('file_id'):
                        if media.get('tipo') == 'foto':
                            await context.bot.send_photo(
                                chat_id=user_id,
                                photo=media.get('file_id'),
                                caption=texto,
                                parse_mode="HTML",
                                reply_markup=reply_markup,
                                protect_content=config_global.get('proteger_mensajes', True)
                            )
                        elif media.get('tipo') == 'video':
                            await context.bot.send_video(
                                chat_id=user_id,
                                video=media.get('file_id'),
                                caption=texto,
                                parse_mode="HTML",
                                reply_markup=reply_markup,
                                protect_content=config_global.get('proteger_mensajes', True)
                            )
                        elif media.get('tipo') == 'gif':
                            await context.bot.send_animation(
                                chat_id=user_id,
                                animation=media.get('file_id'),
                                caption=texto,
                                parse_mode="HTML",
                                reply_markup=reply_markup,
                                protect_content=config_global.get('proteger_mensajes', True)
                            )
                        elif media.get('tipo') == 'sticker':
                            await context.bot.send_sticker(
                                chat_id=user_id,
                                sticker=media.get('file_id'),
                                protect_content=config_global.get('proteger_mensajes', True)
                            )
                            await context.bot.send_message(
                                chat_id=user_id,
                                text=texto,
                                parse_mode="HTML",
                                reply_markup=reply_markup,
                                protect_content=config_global.get('proteger_mensajes', True)
                            )
                    else:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=texto,
                            parse_mode="HTML",
                            reply_markup=reply_markup,
                            protect_content=config_global.get('proteger_mensajes', True)
                        )
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error enviando a {user_id}: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error en enviar_mensaje_programado: {str(e)}")

# ==================== SOLICITUDES DE UNIÓN ====================
async def handle_join_request(update, context):
    try:
        if not update.chat_join_request:
            return
            
        join_request = update.chat_join_request
        user = join_request.from_user
        chat = join_request.chat
        grupo_id = chat.id
        
        logger.info(f"🔵 Solicitud de {user.first_name} en grupo {grupo_id}")
        
        grupo_config = get_grupo_config(grupo_id)
        config_global = cargar_config()
        
        # Registrar usuario
        registro = cargar_registro()
        user_id = str(user.id)
        
        if user_id not in registro.get('usuarios', {}):
            registro['usuarios'][user_id] = {
                "nombre": user.first_name,
                "username": user.username,
                "veces": 1,
                "fecha": datetime.now().isoformat(),
                "grupo": str(grupo_id)
            }
        else:
            registro['usuarios'][user_id]['veces'] += 1
            registro['usuarios'][user_id]['ultima'] = datetime.now().isoformat()
            registro['usuarios'][user_id]['grupo'] = str(grupo_id)
        
        guardar_registro(registro)
        
        es_reingreso = registro['usuarios'][user_id]['veces'] > 1
        
        variables = obtener_variables(user, chat, grupo_config)
        
        if es_reingreso:
            mensaje = grupo_config.get('mensaje_reingreso', config_default['mensaje_reingreso'])
            media = grupo_config.get('media_reingreso')
            sticker = grupo_config.get('sticker_reingreso')
            gif = grupo_config.get('gif_reingreso')
        else:
            mensaje = grupo_config.get('mensaje_bienvenida', config_default['mensaje_bienvenida'])
            media = grupo_config.get('media_bienvenida')
            sticker = grupo_config.get('sticker_bienvenida')
            gif = grupo_config.get('gif_bienvenida')
        
        mensaje_personalizado = procesar_mensaje(mensaje, variables)
        botones = grupo_config.get('botones_bienvenida', [])
        reply_markup = crear_botones(botones)
        
        # Enviar mensaje al PV
        try:
            if media and media.get('file_id'):
                if media.get('tipo') == 'foto':
                    msg = await context.bot.send_photo(
                        chat_id=user.id,
                        photo=media.get('file_id'),
                        caption=f"👋 ¡Hola {user.first_name}!\n\n{mensaje_personalizado}",
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                        protect_content=config_global.get('proteger_mensajes', True)
                    )
                elif media.get('tipo') == 'video':
                    msg = await context.bot.send_video(
                        chat_id=user.id,
                        video=media.get('file_id'),
                        caption=f"👋 ¡Hola {user.first_name}!\n\n{mensaje_personalizado}",
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                        protect_content=config_global.get('proteger_mensajes', True)
                    )
            elif sticker:
                msg = await context.bot.send_sticker(
                    chat_id=user.id,
                    sticker=sticker,
                    protect_content=config_global.get('proteger_mensajes', True)
                )
                msg = await context.bot.send_message(
                    chat_id=user.id,
                    text=f"👋 ¡Hola {user.first_name}!\n\n{mensaje_personalizado}",
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    protect_content=config_global.get('proteger_mensajes', True)
                )
            elif gif:
                msg = await context.bot.send_animation(
                    chat_id=user.id,
                    animation=gif,
                    caption=f"👋 ¡Hola {user.first_name}!\n\n{mensaje_personalizado}",
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    protect_content=config_global.get('proteger_mensajes', True)
                )
            else:
                msg = await context.bot.send_message(
                    chat_id=user.id,
                    text=f"👋 ¡Hola {user.first_name}!\n\n{mensaje_personalizado}",
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    protect_content=config_global.get('proteger_mensajes', True)
                )
            
            # Fijar mensaje
            if grupo_config.get('fijar_mensaje', False):
                try:
                    await context.bot.pin_chat_message(
                        chat_id=user.id,
                        message_id=msg.message_id
                    )
                    logger.info(f"📌 Mensaje fijado para {user.first_name}")
                except Exception as e:
                    logger.error(f"Error fijando mensaje: {str(e)}")
            
            # Eliminar bienvenida después de tiempo
            tiempo_elim = grupo_config.get('tiempo_eliminacion_bienvenida', 0)
            if tiempo_elim > 0:
                async def eliminar_bienvenida():
                    await asyncio.sleep(tiempo_elim)
                    try:
                        await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
                        logger.info(f"🗑️ Bienvenida eliminada después de {tiempo_elim}s")
                    except:
                        pass
                
                asyncio.create_task(eliminar_bienvenida())
            
            logger.info(f"✅ Bienvenida enviada a {user.first_name}")
            
        except Exception as e:
            logger.error(f"Error enviando bienvenida: {str(e)}")
        
        # Auto-aprobación con retraso
        auto_aprobar = grupo_config.get('auto_aprobar', True)
        tiempo_aprobacion = grupo_config.get('tiempo_aprobacion', 0)
        
        if auto_aprobar:
            if tiempo_aprobacion > 0:
                logger.info(f"⏰ Esperando {tiempo_aprobacion}s para aprobar a {user.first_name}")
                
                async def aprobar_despues():
                    await asyncio.sleep(tiempo_aprobacion)
                    try:
                        await context.bot.approve_chat_join_request(chat_id=grupo_id, user_id=user.id)
                        logger.info(f"✅ {user.first_name} aprobado después de {tiempo_aprobacion}s")
                    except Exception as e:
                        logger.error(f"Error aprobando: {str(e)}")
                
                asyncio.create_task(aprobar_despues())
            else:
                try:
                    await context.bot.approve_chat_join_request(chat_id=grupo_id, user_id=user.id)
                    logger.info(f"✅ {user.first_name} aprobado inmediatamente")
                except Exception as e:
                    logger.error(f"Error aprobando: {str(e)}")
        else:
            logger.info(f"❌ Auto-aprobación desactivada para {user.first_name}")
            await context.bot.send_message(
                chat_id=ID_ADMIN,
                text=f"❌ Solicitud de {user.first_name} - Pendiente"
            )
        
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
        
        old_status = chat_member.old_chat_member.status
        new_status = chat_member.new_chat_member.status
        
        if (old_status in ['member', 'administrator', 'creator'] and 
            new_status in ['left', 'kicked']):
            
            logger.info(f"👋 {user.first_name} salió del grupo {grupo_id}")
            
            grupo_config = get_grupo_config(grupo_id)
            config_global = cargar_config()
            
            variables = obtener_variables(user, chat, grupo_config)
            mensaje = grupo_config.get('mensaje_despedida', config_default['mensaje_despedida'])
            mensaje_personalizado = procesar_mensaje(mensaje, variables)
            
            botones = grupo_config.get('botones_despedida', [])
            reply_markup = crear_botones(botones)
            media = grupo_config.get('media_despedida')
            sticker = grupo_config.get('sticker_despedida')
            gif = grupo_config.get('gif_despedida')
            
            try:
                if media and media.get('file_id'):
                    if media.get('tipo') == 'foto':
                        await context.bot.send_photo(
                            chat_id=user.id,
                            photo=media.get('file_id'),
                            caption=f"👋 ¡Hasta luego {user.first_name}!\n\n{mensaje_personalizado}",
                            parse_mode="HTML",
                            reply_markup=reply_markup,
                            protect_content=config_global.get('proteger_mensajes', True)
                        )
                    elif media.get('tipo') == 'video':
                        await context.bot.send_video(
                            chat_id=user.id,
                            video=media.get('file_id'),
                            caption=f"👋 ¡Hasta luego {user.first_name}!\n\n{mensaje_personalizado}",
                            parse_mode="HTML",
                            reply_markup=reply_markup,
                            protect_content=config_global.get('proteger_mensajes', True)
                        )
                elif sticker:
                    await context.bot.send_sticker(
                        chat_id=user.id,
                        sticker=sticker,
                        protect_content=config_global.get('proteger_mensajes', True)
                    )
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=f"👋 ¡Hasta luego {user.first_name}!\n\n{mensaje_personalizado}",
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                        protect_content=config_global.get('proteger_mensajes', True)
                    )
                elif gif:
                    await context.bot.send_animation(
                        chat_id=user.id,
                        animation=gif,
                        caption=f"👋 ¡Hasta luego {user.first_name}!\n\n{mensaje_personalizado}",
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                        protect_content=config_global.get('proteger_mensajes', True)
                    )
                else:
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=f"👋 ¡Hasta luego {user.first_name}!\n\n{mensaje_personalizado}",
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                        protect_content=config_global.get('proteger_mensajes', True)
                    )
                logger.info(f"✅ Despedida enviada a {user.first_name}")
            except Exception as e:
                logger.error(f"Error enviando despedida: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error en handle_chat_member_update: {str(e)}")

# ==================== BORRAR MENSAJES DEL USUARIO ====================
async def borrar_mensajes_usuario(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    
    if update.message.chat.type != 'private':
        return
    
    config = cargar_config()
    if not config.get('borrar_mensajes_pv', True):
        return
    
    try:
        await context.bot.delete_message(
            chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
        logger.info("🗑️ Mensaje de usuario borrado instantáneamente")
    except Exception as e:
        logger.error(f"Error borrando mensaje de usuario: {str(e)}")

# ==================== INICIO ====================
def main():
    logger.info("🚀 Iniciando Bot Avanzado Pro...")
    
    application = Application.builder().token(TOKEN).build()
    
    # Comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancelar", cancelar))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="menu_|welcome_|goodbye_|reingreso_|media_|reset_|auto_|t_|proteger_|borrar_|bt_|elim_|alert_|edit_|delete_|custom_|copy_|mensaje_|botones_|fijar_|reglas_"))
    
    # Configuración
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_config))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.Sticker & ~filters.COMMAND, handle_config))
    
    # Borrar mensajes de usuario en PV
    application.add_handler(MessageHandler(filters.ALL & filters.ChatType.PRIVATE, borrar_mensajes_usuario))
    
    # Solicitudes de unión y salidas
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    application.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    
    # Iniciar mensajes programados
    if application.job_queue:
        config = cargar_config()
        for gid, grupo_config in config.get('grupos', {}).items():
            for i, msg in enumerate(grupo_config.get('mensajes_programados', [])):
                intervalo = msg.get('intervalo', 3600)
                application.job_queue.run_repeating(
                    enviar_mensaje_programado,
                    interval=intervalo,
                    first=5,
                    name=f"msg_{gid}_{i+1}",
                    chat_id=int(gid),
                    user_id=int(gid)
                )
                logger.info(f"📨 Mensaje programado en grupo {gid} cada {intervalo/60:.0f} min")
    
    logger.info("✅ Bot iniciado correctamente!")
    logger.info(f"👤 Admin ID: {ID_ADMIN}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
