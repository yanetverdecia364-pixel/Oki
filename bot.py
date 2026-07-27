import os
import json
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
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
    "botones_repetidos": [],
    "media_bienvenida": None,
    "sticker_bienvenida": None,
    "gif_bienvenida": None,
    "mensajes_programados": [],
    "auto_aprobar": True,
    "tiempo_aprobacion": 0,
    "proteger_mensajes": True,
    "fijar_mensaje": False,
    "tipo_fijar": "bienvenida",
    "tiempo_eliminacion_bienvenida": 0,
    "tiempo_eliminacion_repetidos": 0,
    "reglas": "",
    "share_text": "🔞 𝘜́𝘯𝘦𝘵𝘦 𝘢𝘭 𝘮𝘦𝘫𝘰𝘳 𝘨𝘳𝘶𝘱𝘰 +𝟭𝟴 𝘺 𝘥𝘪𝘴𝘧𝘳𝘶𝘵𝘢😏 🔥 https://kut.lat/eEva",
    "mensajes_activos": {}
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
            "botones_repetidos": [],
            "media_bienvenida": None,
            "sticker_bienvenida": None,
            "gif_bienvenida": None,
            "auto_aprobar": True,
            "tiempo_aprobacion": 0,
            "proteger_mensajes": True,
            "fijar_mensaje": False,
            "tipo_fijar": "bienvenida",
            "tiempo_eliminacion_bienvenida": 0,
            "tiempo_eliminacion_repetidos": 0,
            "reglas": "",
            "share_text": config_default['share_text'],
            "mensajes_programados": [],
            "mensajes_activos": {}
        }
        guardar_config(config)
    
    return config['grupos'][gid]

def guardar_grupo_config(grupo_id, grupo_config):
    config = cargar_config()
    config['grupos'][str(grupo_id)] = grupo_config
    guardar_config(config)

# ==================== VARIABLES PARA MENSAJES ====================
def obtener_variables(user, chat=None, grupo_config=None):
    return {
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
    
    # Botón SHARE por defecto
    if share_text:
        fila.append(InlineKeyboardButton("📤 Compartir grupo", switch_inline_query=share_text))
    
    for b in botones_config:
        tipo = b.get('tipo', 'url')
        
        if tipo == 'url':
            fila.append(InlineKeyboardButton(b['texto'], url=b['url']))
        elif tipo == 'share':
            texto_share = b.get('share_text', share_text or '¡Mira este grupo!')
            fila.append(InlineKeyboardButton(b['texto'], switch_inline_query=texto_share))
        elif tipo == 'alert':
            fila.append(InlineKeyboardButton(b['texto'], callback_data=f"alert_{b.get('alert_text', '¡Mensaje!')}"))
        elif tipo == 'copy':
            fila.append(InlineKeyboardButton(b['texto'], callback_data=f"copy_{b.get('copy_text', 'Texto copiado')}"))
        
        # Cada 2 botones, crear nueva fila (excepto si es el último)
        if len(fila) >= 2:
            keyboard.append(fila)
            fila = []
    
    # Agregar la última fila si tiene botones
    if fila:
        keyboard.append(fila)
    
    return InlineKeyboardMarkup(keyboard) if keyboard else None

# ==================== PROCESAR BOTONES ====================
def procesar_botones_avanzado(texto):
    if not texto:
        return []
    
    botones = []
    
    # Dividir por filas (salto de línea)
    lineas = texto.strip().split('\n')
    
    for linea in lineas:
        if not linea.strip():
            continue
        
        # Verificar si tiene && (misma fila)
        if ' && ' in linea:
            items = linea.split(' && ')
            for item in items:
                if ' - ' in item:
                    partes = item.strip().split(' - ', 1)
                    boton = crear_boton_desde_texto(partes[0].strip(), partes[1].strip())
                    if boton:
                        botones.append(boton)
        else:
            # Botón normal en su propia fila
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

# ==================== BOTONES POR DEFECTO ====================
def botones_por_defecto():
    return [
        {"tipo": "alert", "texto": "⚠️ Aviso", "alert_text": "¡Lee las reglas del grupo!"},
    ]

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
        [InlineKeyboardButton("📨 Mensajes Programados", callback_data=f"menu_mensajes_{grupo_id}")],
        [InlineKeyboardButton("📋 Reglas del Grupo", callback_data=f"menu_reglas_{grupo_id}")],
        [InlineKeyboardButton("✅ Auto-Aprobación", callback_data=f"menu_auto_{grupo_id}")],
        [InlineKeyboardButton("⏰ Tiempo Aprobación", callback_data=f"menu_tiempo_{grupo_id}")],
        [InlineKeyboardButton("📌 Fijar Mensaje", callback_data=f"menu_fijar_{grupo_id}")],
        [InlineKeyboardButton("⏰ Eliminar Bienvenida", callback_data=f"menu_eliminar_bienvenida_{grupo_id}")],
        [InlineKeyboardButton("⏰ Eliminar Repetidos", callback_data=f"menu_eliminar_repetidos_{grupo_id}")],
        [InlineKeyboardButton("📤 Texto Compartir", callback_data=f"menu_share_{grupo_id}")],
        [InlineKeyboardButton("👁️ Vista Previa", callback_data=f"menu_preview_{grupo_id}")],
        [InlineKeyboardButton("📊 Estado Grupo", callback_data=f"menu_status_{grupo_id}")],
        [InlineKeyboardButton("🔄 Resetear Grupo", callback_data=f"menu_reset_{grupo_id}")],
        [InlineKeyboardButton("📋 Listar Grupos", callback_data="menu_list_grupos")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    texto = (
        f"🤖 *CONFIGURACIÓN*\n"
        f"{'═' * 25}\n\n"
        f"📌 Grupo: `{grupo_id}`\n"
        f"✅ Auto-Aprobación: {'ON' if grupo_config.get('auto_aprobar', True) else 'OFF'}\n"
        f"⏰ Tiempo: {grupo_config.get('tiempo_aprobacion', 0)}s\n"
        f"📌 Fijar: {'✅' if grupo_config.get('fijar_mensaje', False) else '❌'}\n"
        f"⏰ Eliminar Bienvenida: {grupo_config.get('tiempo_eliminacion_bienvenida', 0)}s\n"
        f"⏰ Eliminar Repetidos: {grupo_config.get('tiempo_eliminacion_repetidos', 0)}s\n\n"
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
        [InlineKeyboardButton("📝 Editar Texto", callback_data=f"welcome_text_{grupo_id}")],
        [InlineKeyboardButton("🖼️ Multimedia", callback_data=f"welcome_media_{grupo_id}")],
        [InlineKeyboardButton("🔘 Botones", callback_data=f"welcome_buttons_{grupo_id}")],
        [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
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
        f"Botones {estado_botones}\n\n"
        f"Selecciona qué configurar:",
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
            if msg.get('sticker'):
                texto += "   ⭐ Con sticker\n"
            elif msg.get('media'):
                texto += "   🖼️ Con media\n"
            if msg.get('botones'):
                texto += f"   🔘 {len(msg.get('botones', []))} botones\n"
    else:
        texto += "No hay mensajes programados.\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Agregar Texto", callback_data=f"mensaje_add_text_{grupo_id}")],
        [InlineKeyboardButton("➕ Agregar Sticker", callback_data=f"mensaje_add_sticker_{grupo_id}")],
        [InlineKeyboardButton("🔘 Agregar Botones", callback_data=f"mensaje_add_botones_{grupo_id}")],
        [InlineKeyboardButton("🗑️ Eliminar", callback_data=f"mensaje_del_{grupo_id}")],
        [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
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
        await query.answer(data.replace('alert_', ''), show_alert=True)
        return
    
    if data.startswith("copy_"):
        await query.answer(f"📋 Copiado:\n{data.replace('copy_', '')}", show_alert=True)
        return
    
    if data.startswith("edit_"):
        await query.edit_message_text(f"✏️ *Editado:*\n\n{data.replace('edit_', '')}", parse_mode="Markdown")
        return
    
    if data == "delete_msg":
        try:
            await query.delete_message()
        except:
            pass
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
    
    # ========== MENÚ MENSAJES PROGRAMADOS ==========
    if data.startswith("menu_mensajes_"):
        await menu_mensajes(update, context, grupo_id)
        return
    
    # ========== TEXTO BIENVENIDA ==========
    if data.startswith("welcome_text_"):
        await query.edit_message_text(
            "✏️ *Editar Mensaje de Bienvenida*\n\n"
            "Envía el nuevo mensaje.\n\n"
            "Formatos HTML soportados:\n"
            "• `<b>bold</b>` - Negrita\n"
            "• `<i>italic</i>` - Cursiva\n"
            "• `<spoiler>spoiler</spoiler>` - Spoiler\n"
            "• `<blockquote>quote</blockquote>` - Cita\n"
            "• `<a href=\"url\">texto</a>` - Enlace\n\n"
            "Variables:\n"
            "• `{NAME}` - Nombre\n"
            "• `{MENTION}` - Mención\n"
            "• `{USERNAME}` - @username\n"
            "• `{GROUPNAME}` - Grupo\n"
            "• `{RULES}` - Reglas\n\n"
            "Ejemplo:\n"
            "`<b>¡Bienvenido {MENTION}!</b>`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'welcome_text'
        context.user_data['grupo_id'] = grupo_id
        return
    
    # ========== MULTIMEDIA BIENVENIDA ==========
    if data.startswith("welcome_media_"):
        keyboard = [
            [InlineKeyboardButton("🖼️ Foto", callback_data=f"media_foto_{grupo_id}")],
            [InlineKeyboardButton("🔵 GIF", callback_data=f"media_gif_{grupo_id}")],
            [InlineKeyboardButton("⭐ Sticker", callback_data=f"media_sticker_{grupo_id}")],
            [InlineKeyboardButton("🗑️ Eliminar", callback_data=f"media_delete_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_welcome_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        media = grupo_config.get('media_bienvenida')
        sticker = grupo_config.get('sticker_bienvenida')
        gif = grupo_config.get('gif_bienvenida')
        
        estado = []
        if media:
            estado.append("📸 Foto")
        if sticker:
            estado.append("⭐ Sticker")
        if gif:
            estado.append("🔵 GIF")
        
        await query.edit_message_text(
            f"🖼️ *Multimedia*\n\nEstado: {', '.join(estado) if estado else '❌ No hay multimedia'}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("media_foto_"):
        await query.edit_message_text("📸 Envía la foto que deseas usar.")
        context.user_data['esperando'] = 'media_foto'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("media_gif_"):
        await query.edit_message_text("🔵 Envía el GIF que deseas usar.")
        context.user_data['esperando'] = 'media_gif'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("media_sticker_"):
        await query.edit_message_text("⭐ Envía el sticker que deseas usar.")
        context.user_data['esperando'] = 'media_sticker'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("media_delete_"):
        grupo_config['media_bienvenida'] = None
        grupo_config['sticker_bienvenida'] = None
        grupo_config['gif_bienvenida'] = None
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("✅ Multimedia eliminada")
        await menu_welcome(update, context, grupo_id)
        return
    
    # ========== BOTONES BIENVENIDA ==========
    if data.startswith("welcome_buttons_"):
        keyboard = [
            [InlineKeyboardButton("➕ Agregar Botones", callback_data=f"botones_add_{grupo_id}")],
            [InlineKeyboardButton("📋 Botones por defecto", callback_data=f"botones_defecto_{grupo_id}")],
            [InlineKeyboardButton("🗑️ Eliminar Todos", callback_data=f"botones_clear_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_welcome_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        botones = grupo_config.get('botones_bienvenida', [])
        texto = f"🔘 *Botones*\n\n"
        if botones:
            for i, b in enumerate(botones, 1):
                texto += f"{i}. {b['texto']} ({b.get('tipo', 'url')})\n"
        else:
            texto += "No hay botones.\n"
        
        await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
        return
    
    if data.startswith("botones_add_"):
        await query.edit_message_text(
            "✏️ *Agregar Botones*\n\n"
            "Formato:\n"
            "• Normal: `Título - t.me/enlace`\n"
            "• Misma fila: `T1 - link1 && T2 - link2`\n"
            "• Popup: `Título - popup:Texto`\n"
            "• Share: `Título - share:Texto`\n"
            "• Copy: `Título - copy:Texto`\n\n"
            "Ejemplo:\n"
            "`📢 Canal - t.me/mi_canal && 📋 Reglas - t.me/reglas`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'botones_bienvenida'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("botones_defecto_"):
        if 'botones_bienvenida' not in grupo_config:
            grupo_config['botones_bienvenida'] = []
        grupo_config['botones_bienvenida'].extend(botones_por_defecto())
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("✅ Botones por defecto agregados")
        await menu_welcome(update, context, grupo_id)
        return
    
    if data.startswith("botones_clear_"):
        grupo_config['botones_bienvenida'] = []
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("✅ Botones eliminados")
        await menu_welcome(update, context, grupo_id)
        return
    
    # ========== MENSAJES PROGRAMADOS ==========
    if data.startswith("mensaje_add_text_"):
        await query.edit_message_text(
            "📝 *Agregar Mensaje de Texto*\n\n"
            "Envía: `segundos|mensaje`\n"
            "Ejemplo: `120|¡Hola {NAME}!`\n\n"
            "Mínimo 60 segundos\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'addmsg_text'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("mensaje_add_sticker_"):
        await query.edit_message_text(
            "⭐ *Agregar Mensaje con Sticker*\n\n"
            "Envía: `segundos`\n"
            "Luego envía el sticker.\n\n"
            "Ejemplo: `120`\n"
            "Mínimo 60 segundos\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'addmsg_sticker'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("mensaje_add_botones_"):
        await query.edit_message_text(
            "🔘 *Agregar Botones a Mensaje Programado*\n\n"
            "Formato: `Título - t.me/enlace`\n"
            "Misma fila: `T1 - link1 && T2 - link2`\n\n"
            "Ejemplo: `📢 Canal - t.me/canal && 📋 Reglas - t.me/reglas`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'addmsg_botones'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("mensaje_del_"):
        await query.edit_message_text(
            "🗑️ *Eliminar Mensaje*\n\n"
            "Envía el número: `1`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'delmsg'
        context.user_data['grupo_id'] = grupo_id
        return
    
    # ========== REGLAS ==========
    if data.startswith("menu_reglas_"):
        await query.edit_message_text(
            "📋 *Reglas del Grupo*\n\n"
            "Envía las reglas.\n\n"
            "Variables: `{NAME}`, `{MENTION}`, `{GROUPNAME}`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'reglas'
        context.user_data['grupo_id'] = grupo_id
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
        await query.edit_message_text("✅ Activada")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    if data.startswith("auto_off_"):
        grupo_config['auto_aprobar'] = False
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("❌ Desactivada")
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
            f"⏰ *TIEMPO*\n\nActual: {tiempo}s",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("t_"):
        segundos = int(data.split('_')[1])
        grupo_config['tiempo_aprobacion'] = segundos
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text(f"✅ {segundos}s")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    # ========== FIJAR MENSAJE ==========
    if data.startswith("menu_fijar_"):
        fijar = grupo_config.get('fijar_mensaje', False)
        tipo_fijar = grupo_config.get('tipo_fijar', 'bienvenida')
        
        keyboard = [
            [InlineKeyboardButton("✅ Activar" if not fijar else "✅ Ya Activado", callback_data=f"fijar_on_{grupo_id}")],
            [InlineKeyboardButton("❌ Desactivar" if fijar else "❌ Ya Desactivado", callback_data=f"fijar_off_{grupo_id}")],
            [InlineKeyboardButton("📌 Fijar Bienvenida" if tipo_fijar != "bienvenida" else "✅ Bienvenida", callback_data=f"fijar_tipo_bienvenida_{grupo_id}")],
            [InlineKeyboardButton("📌 Fijar Repetido" if tipo_fijar != "repetido" else "✅ Repetido", callback_data=f"fijar_tipo_repetido_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📌 *FIJAR MENSAJE*\n\n"
            f"Estado: {'✅ Activado' if fijar else '❌ Desactivado'}\n"
            f"Tipo: {tipo_fijar}\n\n"
            f"Selecciona qué mensaje fijar en el chat del usuario.",
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
    
    if data.startswith("fijar_tipo_bienvenida_"):
        grupo_config['tipo_fijar'] = "bienvenida"
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("✅ Fijará mensaje de BIENVENIDA")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    if data.startswith("fijar_tipo_repetido_"):
        grupo_config['tipo_fijar'] = "repetido"
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("✅ Fijará mensaje REPETIDO")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    # ========== ELIMINAR BIENVENIDA ==========
    if data.startswith("menu_eliminar_bienvenida_"):
        keyboard = [
            [InlineKeyboardButton("❌ Desactivar (0s)", callback_data=f"elim_b_0_{grupo_id}")],
            [InlineKeyboardButton("⏰ 30s", callback_data=f"elim_b_30_{grupo_id}")],
            [InlineKeyboardButton("⏰ 60s", callback_data=f"elim_b_60_{grupo_id}")],
            [InlineKeyboardButton("⏰ 120s", callback_data=f"elim_b_120_{grupo_id}")],
            [InlineKeyboardButton("⏰ 300s", callback_data=f"elim_b_300_{grupo_id}")],
            [InlineKeyboardButton("⏰ 600s", callback_data=f"elim_b_600_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        tiempo = grupo_config.get('tiempo_eliminacion_bienvenida', 0)
        await query.edit_message_text(
            f"🗑️ *ELIMINAR BIENVENIDA*\n\n"
            f"Actual: {tiempo}s\n\n"
            f"Los mensajes de bienvenida se eliminarán después de este tiempo.\n"
            f"0 = No eliminar",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("elim_b_"):
        segundos = int(data.split('_')[2])
        grupo_config['tiempo_eliminacion_bienvenida'] = segundos
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text(f"✅ Bienvenida se eliminará después de {segundos}s")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    # ========== ELIMINAR REPETIDOS ==========
    if data.startswith("menu_eliminar_repetidos_"):
        keyboard = [
            [InlineKeyboardButton("❌ Desactivar (0s)", callback_data=f"elim_r_0_{grupo_id}")],
            [InlineKeyboardButton("⏰ 30s", callback_data=f"elim_r_30_{grupo_id}")],
            [InlineKeyboardButton("⏰ 60s", callback_data=f"elim_r_60_{grupo_id}")],
            [InlineKeyboardButton("⏰ 120s", callback_data=f"elim_r_120_{grupo_id}")],
            [InlineKeyboardButton("⏰ 300s", callback_data=f"elim_r_300_{grupo_id}")],
            [InlineKeyboardButton("⏰ 600s", callback_data=f"elim_r_600_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        tiempo = grupo_config.get('tiempo_eliminacion_repetidos', 0)
        await query.edit_message_text(
            f"🗑️ *ELIMINAR REPETIDOS*\n\n"
            f"Actual: {tiempo}s\n\n"
            f"Los mensajes repetidos se eliminarán después de este tiempo.\n"
            f"0 = No eliminar",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("elim_r_"):
        segundos = int(data.split('_')[2])
        grupo_config['tiempo_eliminacion_repetidos'] = segundos
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text(f"✅ Repetidos se eliminarán después de {segundos}s")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    # ========== TEXTO COMPARTIR ==========
    if data.startswith("menu_share_"):
        await query.edit_message_text(
            "📤 *Texto para Compartir*\n\n"
            "Envía el texto que aparecerá cuando alguien use el botón COMPARTIR.\n\n"
            "Ejemplo actual:\n"
            f"`{grupo_config.get('share_text', 'No configurado')}`\n\n"
            "Puedes usar variables: `{GROUPNAME}`, `{NAME}`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'share_text'
        context.user_data['grupo_id'] = grupo_id
        return
    
    # ========== VISTA PREVIA ==========
    if data.startswith("menu_preview_"):
        await preview_grupo(update, context, grupo_id)
        await query.delete_message()
        return
    
    # ========== STATUS ==========
    if data.startswith("menu_status_"):
        registro = cargar_registro()
        usuarios_grupo = [u for u in registro.get('usuarios', {}).values() if u.get('grupo') == str(grupo_id)]
        
        texto = (
            f"📊 *ESTADO*\n\n"
            f"👥 Usuarios: {len(usuarios_grupo)}\n"
            f"🔘 Botones: {len(grupo_config.get('botones_bienvenida', []))}\n"
            f"📨 Programados: {len(grupo_config.get('mensajes_programados', []))}\n"
            f"🖼️ Media: {'✅' if grupo_config.get('media_bienvenida') else '❌'}\n"
            f"⭐ Sticker: {'✅' if grupo_config.get('sticker_bienvenida') else '❌'}"
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
            f"⚠️ *¿RESETEAR?*\nNo se puede deshacer.",
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
            "botones_repetidos": [],
            "media_bienvenida": None,
            "sticker_bienvenida": None,
            "gif_bienvenida": None,
            "auto_aprobar": True,
            "tiempo_aprobacion": 0,
            "proteger_mensajes": True,
            "fijar_mensaje": False,
            "tipo_fijar": "bienvenida",
            "tiempo_eliminacion_bienvenida": 0,
            "tiempo_eliminacion_repetidos": 0,
            "reglas": "",
            "share_text": config_default['share_text'],
            "mensajes_programados": [],
            "mensajes_activos": {}
        }
        guardar_config(config)
        await query.edit_message_text(f"✅ Grupo reseteado")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    # ========== ATRÁS ==========
    if data.startswith("menu_back_"):
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return

# ==================== PREVIEW ====================
async def preview_grupo(update, context, grupo_id):
    grupo_config = get_grupo_config(grupo_id)
    mensaje = grupo_config.get('mensaje_bienvenida', 'No configurado')
    botones = grupo_config.get('botones_bienvenida', [])
    media = grupo_config.get('media_bienvenida')
    sticker = grupo_config.get('sticker_bienvenida')
    gif = grupo_config.get('gif_bienvenida')
    share_text = grupo_config.get('share_text', config_default['share_text'])
    
    variables = {
        "{ID}": "123456789",
        "{NAME}": "Usuario",
        "{MENTION}": '<a href="tg://user?id=123456789">Usuario</a>',
        "{USERNAME}": "@usuario",
        "{GROUPNAME}": "Grupo de Prueba",
        "{RULES}": "Reglas del grupo",
        "{DATE}": datetime.now().strftime("%d/%m/%Y"),
        "{TIME}": datetime.now().strftime("%H:%M"),
    }
    
    mensaje_prueba = procesar_mensaje(mensaje, variables)
    share_text_procesado = procesar_mensaje(share_text, variables)
    reply_markup = crear_botones(botones, share_text_procesado)
    
    try:
        if media and media.get('file_id'):
            await update.callback_query.message.reply_photo(
                photo=media.get('file_id'),
                caption=f"👁️ *Vista previa:*\n\n{mensaje_prueba}",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        elif sticker:
            await update.callback_query.message.reply_sticker(sticker=sticker)
            await update.callback_query.message.reply_text(
                f"👁️ *Vista previa:*\n\n{mensaje_prueba}",
                parse_mode="HTML",
                reply_markup=reply_markup
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
        await update.callback_query.message.reply_text(f"❌ Error: {str(e)}")

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
    
    # ========== TEXTO BIENVENIDA ==========
    if estado == 'welcome_text':
        # Si es reenvío de un mensaje, obtener el texto del mensaje reenviado
        if update.message.forward_from or update.message.forward_from_chat:
            if update.message.text:
                grupo_config['mensaje_bienvenida'] = update.message.text
            else:
                await update.message.reply_text("❌ No se pudo obtener el texto del mensaje reenviado.")
                return
        else:
            grupo_config['mensaje_bienvenida'] = update.message.text
        
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text("✅ Mensaje actualizado.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return
    
    # ========== SHARE TEXT ==========
    if estado == 'share_text':
        grupo_config['share_text'] = update.message.text
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text("✅ Texto para compartir actualizado.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return
    
    # ========== REGLAS ==========
    if estado == 'reglas':
        grupo_config['reglas'] = update.message.text
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text("✅ Reglas guardadas.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return
    
    # ========== MULTIMEDIA ==========
    if estado == 'media_foto':
        if update.message.photo:
            grupo_config['media_bienvenida'] = {"tipo": "foto", "file_id": update.message.photo[-1].file_id}
            guardar_grupo_config(grupo_id, grupo_config)
            await update.message.reply_text("✅ Foto guardada.")
        else:
            await update.message.reply_text("❌ Envía una foto.")
            return
        context.user_data.clear()
        await menu_welcome(update, context, grupo_id)
        return
    
    if estado == 'media_gif':
        if update.message.animation or update.message.document:
            file_id = update.message.animation.file_id if update.message.animation else update.message.document.file_id
            grupo_config['gif_bienvenida'] = file_id
            guardar_grupo_config(grupo_id, grupo_config)
            await update.message.reply_text("✅ GIF guardado.")
        else:
            await update.message.reply_text("❌ Envía un GIF.")
            return
        context.user_data.clear()
        await menu_welcome(update, context, grupo_id)
        return
    
    if estado == 'media_sticker':
        if update.message.sticker:
            grupo_config['sticker_bienvenida'] = update.message.sticker.file_id
            guardar_grupo_config(grupo_id, grupo_config)
            await update.message.reply_text("✅ Sticker guardado.")
        else:
            await update.message.reply_text("❌ Envía un sticker.")
            return
        context.user_data.clear()
        await menu_welcome(update, context, grupo_id)
        return
    
    # ========== BOTONES BIENVENIDA ==========
    if estado == 'botones_bienvenida':
        botones = procesar_botones_avanzado(update.message.text)
        if botones:
            if 'botones_bienvenida' not in grupo_config:
                grupo_config['botones_bienvenida'] = []
            grupo_config['botones_bienvenida'].extend(botones)
            guardar_grupo_config(grupo_id, grupo_config)
            await update.message.reply_text(f"✅ {len(botones)} botones agregados")
        else:
            await update.message.reply_text("❌ Formato incorrecto.")
        context.user_data.clear()
        await menu_welcome(update, context, grupo_id)
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
            
            if 'mensajes_programados' not in grupo_config:
                grupo_config['mensajes_programados'] = []
            
            grupo_config['mensajes_programados'].append({
                "intervalo": segundos,
                "mensaje": partes[1],
                "media": None,
                "sticker": None,
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
            
            await update.message.reply_text(f"✅ Mensaje cada {segundos/60:.0f} min")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
        context.user_data.clear()
        await menu_mensajes(update, context, grupo_id)
        return
    
    if estado == 'addmsg_sticker':
        try:
            segundos = float(update.message.text)
            if segundos < 60:
                await update.message.reply_text("⚠️ Mínimo 60 segundos")
                return
            
            context.user_data['esperando_sticker'] = segundos
            await update.message.reply_text(f"📤 Envía el sticker para cada {segundos/60:.0f} min")
            context.user_data['esperando'] = 'addmsg_sticker_file'
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
        return
    
    if estado == 'addmsg_sticker_file':
        try:
            segundos = context.user_data.get('esperando_sticker', 0)
            if not segundos:
                return
            
            if not update.message.sticker:
                await update.message.reply_text("❌ Envía un sticker.")
                return
            
            if 'mensajes_programados' not in grupo_config:
                grupo_config['mensajes_programados'] = []
            
            grupo_config['mensajes_programados'].append({
                "intervalo": segundos,
                "mensaje": "¡Hola {NAME}! Recuerda visitar el grupo 🎉",
                "media": None,
                "sticker": update.message.sticker.file_id,
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
            
            await update.message.reply_text(f"✅ Sticker cada {segundos/60:.0f} min")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
        context.user_data.clear()
        await menu_mensajes(update, context, grupo_id)
        return
    
    if estado == 'addmsg_botones':
        botones = procesar_botones_avanzado(update.message.text)
        if not botones:
            await update.message.reply_text("❌ Formato incorrecto.")
            context.user_data.clear()
            await menu_mensajes(update, context, grupo_id)
            return
        
        mensajes = grupo_config.get('mensajes_programados', [])
        if not mensajes:
            await update.message.reply_text("❌ Primero agrega un mensaje.")
            context.user_data.clear()
            await menu_mensajes(update, context, grupo_id)
            return
        
        ultimo = mensajes[-1]
        if 'botones' not in ultimo:
            ultimo['botones'] = []
        ultimo['botones'].extend(botones)
        guardar_grupo_config(grupo_id, grupo_config)
        
        await update.message.reply_text(f"✅ {len(botones)} botones agregados")
        context.user_data.clear()
        await menu_mensajes(update, context, grupo_id)
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
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
        context.user_data.clear()
        await menu_mensajes(update, context, grupo_id)
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
        share_text = grupo_config.get('share_text', config_default['share_text'])
        
        try:
            chat_members = await context.bot.get_chat_administrators(grupo_id)
            user_ids = [m.user.id for m in chat_members]
        except Exception as e:
            logger.error(f"Error obteniendo miembros: {str(e)}")
            return
        
        if not user_ids:
            logger.warning(f"No hay miembros en grupo {grupo_id}")
            return
        
        try:
            chat = await context.bot.get_chat(grupo_id)
        except:
            chat = None
        
        for msg_config in grupo_config.get('mensajes_programados', []):
            mensaje = msg_config.get('mensaje', '')
            media = msg_config.get('media')
            sticker = msg_config.get('sticker')
            botones = msg_config.get('botones', [])
            
            for user_id in user_ids:
                try:
                    try:
                        user = await context.bot.get_chat(user_id)
                    except:
                        continue
                    
                    variables = obtener_variables(user, chat, grupo_config)
                    texto = procesar_mensaje(mensaje, variables)
                    share_text_procesado = procesar_mensaje(share_text, variables)
                    reply_markup = crear_botones(botones, share_text_procesado)
                    
                    # Enviar sticker primero si existe
                    if sticker:
                        try:
                            await context.bot.send_sticker(
                                chat_id=user_id,
                                sticker=sticker,
                                protect_content=config_global.get('proteger_mensajes', True)
                            )
                            logger.info(f"✅ Sticker enviado a {user_id}")
                        except Exception as e:
                            logger.error(f"Error enviando sticker: {str(e)}")
                    
                    # Enviar mensaje con texto
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
                    else:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=texto,
                            parse_mode="HTML",
                            reply_markup=reply_markup,
                            protect_content=config_global.get('proteger_mensajes', True)
                        )
                    
                    # Eliminar mensaje después de tiempo (si está configurado)
                    tiempo_elim = grupo_config.get('tiempo_eliminacion_repetidos', 0)
                    if tiempo_elim > 0:
                        # Guardar para eliminar después
                        pass
                    
                    logger.info(f"✅ Mensaje enviado a {user_id}")
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
        
        grupo_config = get_grupo_config(grupo_id)
        config_global = cargar_config()
        share_text = grupo_config.get('share_text', config_default['share_text'])
        
        registro = cargar_registro()
        user_id = str(user.id)
        if user_id not in registro.get('usuarios', {}):
            registro['usuarios'][user_id] = {"nombre": user.first_name, "username": user.username, "veces": 1, "fecha": datetime.now().isoformat(), "grupo": str(grupo_id)}
        else:
            registro['usuarios'][user_id]['veces'] += 1
        guardar_registro(registro)
        
        es_reingreso = registro['usuarios'][user_id]['veces'] > 1
        variables = obtener_variables(user, chat, grupo_config)
        
        if es_reingreso:
            mensaje = grupo_config.get('mensaje_reingreso', config_default['mensaje_reingreso'])
        else:
            mensaje = grupo_config.get('mensaje_bienvenida', config_default['mensaje_bienvenida'])
        
        mensaje_personalizado = procesar_mensaje(mensaje, variables)
        botones = grupo_config.get('botones_bienvenida', [])
        share_text_procesado = procesar_mensaje(share_text, variables)
        reply_markup = crear_botones(botones, share_text_procesado)
        media = grupo_config.get('media_bienvenida')
        sticker = grupo_config.get('sticker_bienvenida')
        gif = grupo_config.get('gif_bienvenida')
        
        try:
            if media and media.get('file_id'):
                if media.get('tipo') == 'foto':
                    msg = await context.bot.send_photo(
                        chat_id=user.id,
                        photo=media.get('file_id'),
                        caption=f"👋 ¡Hola!\n\n{mensaje_personalizado}",
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                        protect_content=True
                    )
                elif media.get('tipo') == 'video':
                    msg = await context.bot.send_video(
                        chat_id=user.id,
                        video=media.get('file_id'),
                        caption=f"👋 ¡Hola!\n\n{mensaje_personalizado}",
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                        protect_content=True
                    )
            elif sticker:
                await context.bot.send_sticker(chat_id=user.id, sticker=sticker, protect_content=True)
                msg = await context.bot.send_message(
                    chat_id=user.id,
                    text=f"👋 ¡Hola!\n\n{mensaje_personalizado}",
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    protect_content=True
                )
            elif gif:
                msg = await context.bot.send_animation(
                    chat_id=user.id,
                    animation=gif,
                    caption=f"👋 ¡Hola!\n\n{mensaje_personalizado}",
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    protect_content=True
                )
            else:
                msg = await context.bot.send_message(
                    chat_id=user.id,
                    text=f"👋 ¡Hola!\n\n{mensaje_personalizado}",
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    protect_content=True
                )
            
            # Fijar mensaje (Bienvenida)
            if grupo_config.get('fijar_mensaje', False) and grupo_config.get('tipo_fijar', 'bienvenida') == 'bienvenida':
                try:
                    await context.bot.pin_chat_message(chat_id=user.id, message_id=msg.message_id)
                    logger.info(f"📌 Mensaje fijado para {user.first_name}")
                except Exception as e:
                    logger.error(f"Error fijando: {str(e)}")
            
            # Eliminar bienvenida después de tiempo
            tiempo_elim = grupo_config.get('tiempo_eliminacion_bienvenida', 0)
            if tiempo_elim > 0:
                async def eliminar_mensaje():
                    await asyncio.sleep(tiempo_elim)
                    try:
                        await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
                        logger.info(f"🗑️ Mensaje eliminado después de {tiempo_elim}s")
                    except Exception as e:
                        logger.error(f"Error eliminando: {str(e)}")
                asyncio.create_task(eliminar_mensaje())
            
        except Exception as e:
            logger.error(f"Error enviando bienvenida: {str(e)}")
        
        # Auto-aprobación
        auto_aprobar = grupo_config.get('auto_aprobar', True)
        tiempo_aprobacion = grupo_config.get('tiempo_aprobacion', 0)
        
        if auto_aprobar:
            if tiempo_aprobacion > 0:
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
            mensaje = grupo_config.get('mensaje_despedida', config_default['mensaje_despedida'])
            mensaje_personalizado = procesar_mensaje(mensaje, variables)
            
            try:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"👋 ¡Hasta luego!\n\n{mensaje_personalizado}",
                    parse_mode="HTML",
                    protect_content=True
                )
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
    
    try:
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
        logger.info("🗑️ Mensaje de usuario borrado")
    except Exception as e:
        logger.error(f"Error borrando: {str(e)}")

# ==================== INICIO ====================
def main():
    logger.info("🚀 Iniciando Bot Avanzado...")
    
    application = Application.builder().token(TOKEN).build()
    
    # Comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancelar", cancelar))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="menu_|welcome_|media_|botones_|mensaje_|auto_|t_|fijar_|elim_|reset_|alert_|copy_|edit_|delete_|custom_"))
    
    # Configuración
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_config))
    application.add_handler(MessageHandler(filters.PHOTO | filters.ANIMATION | filters.Sticker & ~filters.COMMAND, handle_config))
    
    # Borrar mensajes en PV
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
                logger.info(f"📨 Mensaje en grupo {gid} cada {intervalo/60:.0f} min")
    
    logger.info("✅ Bot iniciado correctamente!")
    logger.info(f"👤 Admin ID: {ID_ADMIN}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
