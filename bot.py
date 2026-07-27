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
        
        if len(fila) >= 2:
            keyboard.append(fila)
            fila = []
    
    if fila:
        keyboard.append(fila)
    
    return InlineKeyboardMarkup(keyboard) if keyboard else None

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
        [InlineKeyboardButton("📝 Mensaje Bienvenida", callback_data=f"menu_welcome_{grupo_id}")],
        [InlineKeyboardButton("👋 Mensaje Despedida", callback_data=f"menu_goodbye_{grupo_id}")],
        [InlineKeyboardButton("🔘 Botones Bienvenida", callback_data=f"menu_botones_bienvenida_{grupo_id}")],
        [InlineKeyboardButton("🔘 Botones Despedida", callback_data=f"menu_botones_despedida_{grupo_id}")],
        [InlineKeyboardButton("🔘 Botones Repetidos", callback_data=f"menu_botones_repetidos_{grupo_id}")],
        [InlineKeyboardButton("📋 Reglas del Grupo", callback_data=f"menu_reglas_{grupo_id}")],
        [InlineKeyboardButton("🖼️ Media", callback_data=f"menu_media_{grupo_id}")],
        [InlineKeyboardButton("📌 Fijar Mensaje", callback_data=f"menu_fijar_{grupo_id}")],
        [InlineKeyboardButton("⏰ Eliminar Bienvenida", callback_data=f"menu_eliminar_{grupo_id}")],
        [InlineKeyboardButton("✅ Auto-Aprobación", callback_data=f"menu_auto_{grupo_id}")],
        [InlineKeyboardButton("⏰ Tiempo Aprobación", callback_data=f"menu_tiempo_{grupo_id}")],
        [InlineKeyboardButton("📨 Mensajes Programados", callback_data=f"menu_mensajes_{grupo_id}")],
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

# ==================== CALLBACKS ====================
async def menu_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ID_ADMIN:
        await query.edit_message_text("❌ No tienes permiso.")
        return
    
    data = query.data
    
    # ========== BOTONES DE ACCIÓN RÁPIDA ==========
    if data.startswith("alert_"):
        alert_text = data.replace('alert_', '')
        await query.answer(alert_text, show_alert=True)
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
    
    # ========== SELECCIONAR GRUPO ==========
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
    
    # ========== MENSAJES ==========
    if data.startswith("menu_welcome_"):
        keyboard = [
            [InlineKeyboardButton("✏️ Editar Bienvenida", callback_data=f"welcome_edit_{grupo_id}")],
            [InlineKeyboardButton("✏️ Editar Reingreso", callback_data=f"reingreso_edit_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"📝 *MENSAJES*\n\nSelecciona qué editar:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("welcome_edit_"):
        await query.edit_message_text(
            "✏️ *Editar Mensaje de Bienvenida*\n\n"
            "Envía el mensaje de bienvenida.\n\n"
            "Variables:\n• `{NAME}` - Nombre\n• `{MENTION}` - Mención\n• `{USERNAME}` - @username\n• `{GROUPNAME}` - Grupo\n\n"
            "Ejemplo: `¡Bienvenido {MENTION}!`\n\nPara cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'welcome'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("reingreso_edit_"):
        await query.edit_message_text(
            "✏️ *Editar Mensaje de Reingreso*\n\n"
            "Envía el mensaje de reingreso.\n\n"
            "Variables:\n• `{NAME}` - Nombre\n• `{MENTION}` - Mención\n\n"
            "Ejemplo: `¡Bienvenido de nuevo {MENTION}!`\n\nPara cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'reingreso'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("menu_goodbye_"):
        await query.edit_message_text(
            "✏️ *Editar Mensaje de Despedida*\n\n"
            "Envía el mensaje de despedida.\n\n"
            "Variables:\n• `{NAME}` - Nombre\n• `{MENTION}` - Mención\n\n"
            "Ejemplo: `¡Hasta luego {MENTION}!`\n\nPara cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'despedida'
        context.user_data['grupo_id'] = grupo_id
        return
    
    # ========== BOTONES ==========
    if data.startswith("menu_botones_bienvenida_"):
        await mostrar_botones_menu(update, context, grupo_id, "bienvenida")
        return
    
    if data.startswith("menu_botones_despedida_"):
        await mostrar_botones_menu(update, context, grupo_id, "despedida")
        return
    
    if data.startswith("menu_botones_repetidos_"):
        await mostrar_botones_menu(update, context, grupo_id, "repetidos")
        return
    
    # ========== AGREGAR BOTONES ==========
    if data.startswith("btn_bienvenida_") or data.startswith("btn_despedida_") or data.startswith("btn_repetidos_"):
        parts = data.split('_')
        tipo_lista = parts[1]
        accion = parts[2]
        
        if accion == 'clear':
            if tipo_lista == "bienvenida":
                grupo_config['botones_bienvenida'] = []
            elif tipo_lista == "despedida":
                grupo_config['botones_despedida'] = []
            else:
                grupo_config['botones_repetidos'] = []
            guardar_grupo_config(grupo_id, grupo_config)
            await query.edit_message_text(f"✅ Botones eliminados")
            await mostrar_botones_menu(update, context, grupo_id, tipo_lista)
            return
        
        await query.edit_message_text(
            "✏️ *Agregar Botón*\n\n"
            "Formato:\n"
            "• URL: `Título - t.me/Link`\n"
            "• Popup: `Título - popup:Texto`\n"
            "• Rules: `Título - rules`\n\n"
            "Ejemplo: `📢 Canal - t.me/mi_canal`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = f"btn_{tipo_lista}_{accion}"
        context.user_data['grupo_id'] = grupo_id
        return
    
    # ========== MEDIA ==========
    if data.startswith("menu_media_"):
        keyboard = [
            [InlineKeyboardButton("📤 Media Bienvenida", callback_data=f"media_welcome_{grupo_id}")],
            [InlineKeyboardButton("📤 Media Reingreso", callback_data=f"media_reingreso_{grupo_id}")],
            [InlineKeyboardButton("📤 Media Despedida", callback_data=f"media_goodbye_{grupo_id}")],
            [InlineKeyboardButton("🗑️ Eliminar Bienvenida", callback_data=f"media_del_welcome_{grupo_id}")],
            [InlineKeyboardButton("🗑️ Eliminar Reingreso", callback_data=f"media_del_reingreso_{grupo_id}")],
            [InlineKeyboardButton("🗑️ Eliminar Despedida", callback_data=f"media_del_goodbye_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"🖼️ *MEDIA*\n\nSelecciona una opción:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("media_welcome_"):
        await query.edit_message_text("📤 Envía la foto/video para BIENVENIDA")
        context.user_data['esperando'] = 'media'
        context.user_data['tipo_media'] = 'bienvenida'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("media_reingreso_"):
        await query.edit_message_text("📤 Envía la foto/video para REINGRESO")
        context.user_data['esperando'] = 'media'
        context.user_data['tipo_media'] = 'reingreso'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("media_goodbye_"):
        await query.edit_message_text("📤 Envía la foto/video para DESPEDIDA")
        context.user_data['esperando'] = 'media'
        context.user_data['tipo_media'] = 'despedida'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("media_del_welcome_"):
        grupo_config['media_bienvenida'] = None
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("✅ Media de bienvenida eliminada")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    if data.startswith("media_del_reingreso_"):
        grupo_config['media_reingreso'] = None
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("✅ Media de reingreso eliminada")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    if data.startswith("media_del_goodbye_"):
        grupo_config['media_despedida'] = None
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("✅ Media de despedida eliminada")
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
    
    # ========== MENSAJES PROGRAMADOS ==========
    if data.startswith("menu_mensajes_"):
        mensajes = grupo_config.get('mensajes_programados', [])
        texto = f"📨 *MENSAJES PROGRAMADOS*\n\n"
        if mensajes:
            for i, msg in enumerate(mensajes, 1):
                seg = msg.get('intervalo', 3600)
                texto += f"{i}. Cada {seg/60:.0f}min: {msg.get('mensaje', '')[:30]}...\n"
        else:
            texto += "No hay mensajes programados.\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Agregar", callback_data=f"addmsg_{grupo_id}")],
            [InlineKeyboardButton("🗑️ Eliminar", callback_data=f"delmsg_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
        return
    
    if data.startswith("addmsg_"):
        await query.edit_message_text(
            "📨 *Agregar Mensaje Programado*\n\n"
            "Envía en formato:\n"
            "`segundos|mensaje`\n\n"
            "Ejemplo: `120|¡Hola {NAME}!`\n\n"
            "Mínimo 60 segundos\n\nPara cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'addmsg'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("delmsg_"):
        await query.edit_message_text(
            "🗑️ *Eliminar Mensaje*\n\n"
            "Envía el número del mensaje:\n`1`\n\nPara cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'delmsg'
        context.user_data['grupo_id'] = grupo_id
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

# ==================== MOSTRAR BOTONES ====================
async def mostrar_botones_menu(update, context, grupo_id, tipo):
    query = update.callback_query
    grupo_config = get_grupo_config(grupo_id)
    
    if tipo == "bienvenida":
        botones = grupo_config.get('botones_bienvenida', [])
        nombre = "BIENVENIDA"
    elif tipo == "despedida":
        botones = grupo_config.get('botones_despedida', [])
        nombre = "DESPEDIDA"
    else:
        botones = grupo_config.get('botones_repetidos', [])
        nombre = "REPETIDOS"
    
    texto = f"🔘 *BOTONES DE {nombre}*\n\n"
    if botones:
        for i, b in enumerate(botones, 1):
            tipo_btn = b.get('tipo', 'url')
            emoji = {'url': '🔗', 'share': '📤', 'alert': '⚠️', 'edit': '✏️', 'delete': '🗑️', 'callback': '⚡'}.get(tipo_btn, '📌')
            texto += f"{i}. {emoji} {b['texto']} ({tipo_btn})\n"
    else:
        texto += "No hay botones configurados.\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ URL", callback_data=f"btn_{tipo}_url_{grupo_id}")],
        [InlineKeyboardButton("📤 Share", callback_data=f"btn_{tipo}_share_{grupo_id}")],
        [InlineKeyboardButton("⚠️ Alert/Popup", callback_data=f"btn_{tipo}_alert_{grupo_id}")],
        [InlineKeyboardButton("✏️ Edit", callback_data=f"btn_{tipo}_edit_{grupo_id}")],
        [InlineKeyboardButton("🗑️ Delete", callback_data=f"btn_{tipo}_delete_{grupo_id}")],
        [InlineKeyboardButton("⚡ Custom", callback_data=f"btn_{tipo}_custom_{grupo_id}")],
        [InlineKeyboardButton("⬆️ Mover Arriba", callback_data=f"btn_{tipo}_up_{grupo_id}")],
        [InlineKeyboardButton("⬇️ Mover Abajo", callback_data=f"btn_{tipo}_down_{grupo_id}")],
        [InlineKeyboardButton("🗑️ Eliminar Todos", callback_data=f"btn_{tipo}_clear_{grupo_id}")],
        [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)

# ==================== PREVIEW ====================
async def preview_grupo(update, context, grupo_id):
    grupo_config = get_grupo_config(grupo_id)
    mensaje = grupo_config.get('mensaje_bienvenida', 'No configurado')
    botones = grupo_config.get('botones_bienvenida', [])
    media = grupo_config.get('media_bienvenida')
    
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
    else:
        await update.callback_query.message.reply_text(
            f"👁️ *Vista previa:*\n\n{mensaje_prueba}",
            parse_mode="HTML",
            reply_markup=reply_markup
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
    
    # ========== REGLAS ==========
    if estado == 'reglas':
        grupo_config['reglas'] = update.message.text
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text("✅ Reglas guardadas correctamente.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return
    
    # ========== MENSAJES ==========
    if estado == 'welcome':
        grupo_config['mensaje_bienvenida'] = update.message.text
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text("✅ Mensaje de bienvenida actualizado.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return
    
    elif estado == 'reingreso':
        grupo_config['mensaje_reingreso'] = update.message.text
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text("✅ Mensaje de reingreso actualizado.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return
    
    elif estado == 'despedida':
        grupo_config['mensaje_despedida'] = update.message.text
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text("✅ Mensaje de despedida actualizado.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return
    
    # ========== MENSAJES PROGRAMADOS ==========
    if estado == 'addmsg':
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
                "media": None
            })
            guardar_grupo_config(grupo_id, grupo_config)
            
            await update.message.reply_text(f"✅ Mensaje programado cada {segundos/60:.0f} minutos")
            context.user_data.clear()
            await menu_principal(update, context, grupo_id=grupo_id)
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
            await menu_principal(update, context, grupo_id=grupo_id)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
        return
    
    # ========== BOTONES ==========
    if estado.startswith('btn_'):
        partes = estado.split('_')
        if len(partes) >= 3:
            tipo_lista = partes[1]
            accion = partes[2]
            
            if tipo_lista == "bienvenida":
                lista_key = "botones_bienvenida"
            elif tipo_lista == "despedida":
                lista_key = "botones_despedida"
            else:
                lista_key = "botones_repetidos"
            
            if lista_key not in grupo_config:
                grupo_config[lista_key] = []
            
            # Procesar botones
            texto = update.message.text
            botones_nuevos = []
            
            # Formato: "Título - t.me/Link"
            if ' - ' in texto:
                partes_txt = texto.split(' - ', 1)
                titulo = partes_txt[0].strip()
                accion_txt = partes_txt[1].strip()
                
                if accion_txt.startswith('popup:') or accion_txt.startswith('alert:'):
                    alert_text = accion_txt.replace('popup:', '').replace('alert:', '')
                    botones_nuevos.append({
                        "tipo": "alert",
                        "texto": titulo,
                        "alert_text": alert_text
                    })
                elif accion_txt == 'rules':
                    botones_nuevos.append({
                        "tipo": "url",
                        "texto": titulo,
                        "url": "https://t.me/"
                    })
                elif accion_txt.startswith('t.me/') or accion_txt.startswith('https://'):
                    if not accion_txt.startswith('http'):
                        accion_txt = 'https://' + accion_txt
                    botones_nuevos.append({
                        "tipo": "url",
                        "texto": titulo,
                        "url": accion_txt
                    })
                else:
                    botones_nuevos.append({
                        "tipo": "url",
                        "texto": titulo,
                        "url": accion_txt
                    })
            else:
                await update.message.reply_text("❌ Formato incorrecto. Usa: `Título - t.me/enlace`")
                return
            
            if botones_nuevos:
                grupo_config[lista_key].extend(botones_nuevos)
                guardar_grupo_config(grupo_id, grupo_config)
                await update.message.reply_text(f"✅ {len(botones_nuevos)} botones agregados")
            else:
                await update.message.reply_text("❌ Formato incorrecto")
            
            context.user_data.clear()
            await menu_principal(update, context, grupo_id=grupo_id)
        return
    
    # ========== MEDIA ==========
    elif estado == 'media':
        tipo = context.user_data.get('tipo_media', 'bienvenida')
        
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            if tipo == 'bienvenida':
                grupo_config['media_bienvenida'] = {"tipo": "foto", "file_id": file_id}
            elif tipo == 'reingreso':
                grupo_config['media_reingreso'] = {"tipo": "foto", "file_id": file_id}
            elif tipo == 'despedida':
                grupo_config['media_despedida'] = {"tipo": "foto", "file_id": file_id}
            guardar_grupo_config(grupo_id, grupo_config)
            await update.message.reply_text(f"✅ Foto guardada para {tipo}")
        elif update.message.video:
            file_id = update.message.video.file_id
            if tipo == 'bienvenida':
                grupo_config['media_bienvenida'] = {"tipo": "video", "file_id": file_id}
            elif tipo == 'reingreso':
                grupo_config['media_reingreso'] = {"tipo": "video", "file_id": file_id}
            elif tipo == 'despedida':
                grupo_config['media_despedida'] = {"tipo": "video", "file_id": file_id}
            guardar_grupo_config(grupo_id, grupo_config)
            await update.message.reply_text(f"✅ Video guardado para {tipo}")
        else:
            await update.message.reply_text("❌ Envía una foto o video.")
            return
        
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return

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
    except:
        pass

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
        
        variables = obtener_variables(user, chat, grupo_config)
        
        # Mensaje de bienvenida
        mensaje = grupo_config.get('mensaje_bienvenida', config_default['mensaje_bienvenida'])
        mensaje_personalizado = procesar_mensaje(mensaje, variables)
        
        botones = grupo_config.get('botones_bienvenida', [])
        reply_markup = crear_botones(botones)
        
        # Enviar mensaje al PV
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=f"👋 ¡Hola {user.first_name}!\n\n{mensaje_personalizado}",
                parse_mode="HTML",
                reply_markup=reply_markup,
                protect_content=config_global.get('proteger_mensajes', True)
            )
        except Exception as e:
            logger.error(f"Error enviando bienvenida: {str(e)}")
        
        # Auto-aprobación
        auto_aprobar = grupo_config.get('auto_aprobar', True)
        
        if auto_aprobar:
            try:
                await context.bot.approve_chat_join_request(chat_id=grupo_id, user_id=user.id)
                logger.info(f"✅ {user.first_name} aprobado")
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
        
        old_status = chat_member.old_chat_member.status
        new_status = chat_member.new_chat_member.status
        
        if (old_status in ['member', 'administrator', 'creator'] and 
            new_status in ['left', 'kicked']):
            
            grupo_config = get_grupo_config(grupo_id)
            config_global = cargar_config()
            
            variables = obtener_variables(user, chat, grupo_config)
            mensaje = grupo_config.get('mensaje_despedida', config_default['mensaje_despedida'])
            mensaje_personalizado = procesar_mensaje(mensaje, variables)
            
            botones = grupo_config.get('botones_despedida', [])
            reply_markup = crear_botones(botones)
            
            try:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"👋 ¡Hasta luego {user.first_name}!\n\n{mensaje_personalizado}",
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    protect_content=config_global.get('proteger_mensajes', True)
                )
            except:
                pass
            
    except Exception as e:
        logger.error(f"Error en handle_chat_member_update: {str(e)}")

# ==================== INICIO ====================
def main():
    logger.info("🚀 Iniciando Bot...")
    
    application = Application.builder().token(TOKEN).build()
    
    # Comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancelar", cancelar))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="menu_|welcome_|reingreso_|media_|reset_|auto_|t_|proteger_|borrar_|bt_|elim_|btn_|alert_|edit_|delete_|custom_|addmsg_|delmsg_|fijar_|reglas_"))
    
    # Configuración
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_config))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_config))
    
    # Borrar mensajes de usuario en PV
    application.add_handler(MessageHandler(filters.ALL & filters.ChatType.PRIVATE, borrar_mensajes_usuario))
    
    # Solicitudes de unión y salidas
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    application.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    
    logger.info("✅ Bot iniciado correctamente!")
    logger.info(f"👤 Admin ID: {ID_ADMIN}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
