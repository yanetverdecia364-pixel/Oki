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

# ==================== CONFIGURACIÓN POR DEFECTO ====================
config_default = {
    "grupos": {},
    "mensaje_bienvenida": "¡Bienvenido al grupo! 🎉\n\nTe damos la bienvenida a nuestra comunidad.",
    "mensaje_reingreso": "¡Bienvenido de nuevo {nombre}! 🎉\n\nNos alegra verte otra vez.",
    "mensaje_despedida": "¡Hasta luego {nombre}! 👋\n\nEsperamos verte pronto.",
    "botones_bienvenida": [],
    "botones_despedida": [],
    "botones_repetidos": [],
    "media_bienvenida": None,
    "media_reingreso": None,
    "media_despedida": None,
    "mensajes_programados": [],
    "formato_texto": "markdown",
    "auto_aprobar": True,
    "tiempo_aprobacion": 0,
    "borrar_mensajes_pv": True,
    "proteger_mensajes": True,
    "tiempo_borrado_pv": 60,
    "tiempo_eliminacion_bienvenida": 0
}

# ==================== FUNCIONES DE CARGA ====================
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
            "mensajes_activos": {}
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

# ==================== SISTEMA DE SHARE ====================
share_estado = {}

async def share_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if user_id not in share_estado:
        share_estado[user_id] = {"paso": 0}
    
    estado = share_estado[user_id]
    
    if estado["paso"] == 0:
        estado["paso"] = 1
        await query.edit_message_text(
            "🎉 *¡FELICIDADES!*\n\n"
            "Has compartido el enlace *1 vez*.\n\n"
            "📌 *Progreso:* 1/2\n\n"
            "Presiona nuevamente *COMPARTIR* para completar el proceso.",
            parse_mode="Markdown"
        )
        await query.answer("✅ ¡Has compartido 1 vez!", show_alert=True)
    
    elif estado["paso"] == 1:
        estado["paso"] = 2
        await query.edit_message_text(
            "🎉 *¡ACCESO CONCEDIDO!*\n\n"
            "Has completado el proceso de *2/2*.\n"
            "Ahora puedes acceder al grupo.\n\n"
            "🔗 *[Haz clic aquí para unirte](https://t.me/+tu_enlace_aqui)*",
            parse_mode="Markdown"
        )
        await query.answer("🎉 ¡Completaste 2/2!", show_alert=True)

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
        [InlineKeyboardButton("🖼️ Media", callback_data=f"menu_media_{grupo_id}")],
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
        f"🗑️ Eliminar bienvenida: {grupo_config.get('tiempo_eliminacion_bienvenida', 0)}s\n\n"
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
    
    # ========== MENSAJES ==========
    if data.startswith("menu_welcome_"):
        keyboard = [
            [InlineKeyboardButton("✏️ Editar Bienvenida", callback_data=f"welcome_edit_{grupo_id}")],
            [InlineKeyboardButton("✏️ Editar Reingreso", callback_data=f"reingreso_edit_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"📝 *MENSAJES - Grupo {grupo_id}*\n\n"
            f"Selecciona qué editar:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("welcome_edit_"):
        await query.edit_message_text(
            "✏️ Envía el mensaje de bienvenida.\n\nVariables disponibles:\n• `{nombre}`\n• `{mention}`\n• `{perfil}`\n• `{id}`\n\nPara cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'welcome'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("reingreso_edit_"):
        await query.edit_message_text(
            "✏️ Envía el mensaje de reingreso.\n\nVariables disponibles:\n• `{nombre}`\n• `{mention}`\n• `{perfil}`\n\nPara cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'reingreso'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("menu_goodbye_"):
        await query.edit_message_text(
            "✏️ Envía el mensaje de despedida.\n\nVariables disponibles:\n• `{nombre}`\n• `{mention}`\n• `{perfil}`\n\nPara cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'despedida'
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
            f"🖼️ *MEDIA - Grupo {grupo_id}*\n\nSelecciona una opción:",
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
            f"✏️ Envía el botón en el formato correspondiente.\n\nPara cancelar: /cancelar"
        )
        context.user_data['esperando'] = f"btn_{tipo_lista}_{accion}"
        context.user_data['grupo_id'] = grupo_id
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
        await query.edit_message_text(
            "📨 *MENSAJES PROGRAMADOS*\n\nComandos en el grupo:\n/addmsg `segundos|mensaje`\n/addmedia `segundos`\n/removemsg `número`\n/listmsg\n\nEjemplo: `/addmsg 120|¡Hola {nombre}!`",
            parse_mode="Markdown"
        )
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
            "mensajes_activos": {}
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
        [InlineKeyboardButton("⚠️ Alert", callback_data=f"btn_{tipo}_alert_{grupo_id}")],
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
    formato = cargar_config().get('formato_texto', 'markdown')
    
    mensaje_prueba = mensaje.replace('{nombre}', 'Usuario')
    mensaje_prueba = mensaje_prueba.replace('{mention}', '@usuario')
    mensaje_prueba = mensaje_prueba.replace('{perfil}', '[Perfil](tg://user?id=123456789)')
    
    reply_markup = crear_botones(botones)
    
    if media and media.get('file_id'):
        if media.get('tipo') == 'foto':
            await update.callback_query.message.reply_photo(
                photo=media.get('file_id'),
                caption=f"👁️ *Vista previa:*\n\n{mensaje_prueba}",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        elif media.get('tipo') == 'video':
            await update.callback_query.message.reply_video(
                video=media.get('file_id'),
                caption=f"👁️ *Vista previa:*\n\n{mensaje_prueba}",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
    else:
        await update.callback_query.message.reply_text(
            f"👁️ *Vista previa:*\n\n{mensaje_prueba}",
            parse_mode="Markdown",
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

# ==================== MENSAJES PROGRAMADOS ====================
async def add_mensaje_grupo(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    
    if update.message.chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ Usa este comando en el grupo.")
        return
    
    grupo_id = update.message.chat_id
    grupo_config = get_grupo_config(grupo_id)
    
    try:
        args = update.message.text.split(' ', 1)
        if len(args) < 2:
            await update.message.reply_text("❌ Usa: `/addmsg segundos|mensaje`")
            return
        
        partes = args[1].split('|', 1)
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
        
        if context.application.job_queue:
            context.application.job_queue.run_repeating(
                enviar_mensaje_programado,
                interval=segundos,
                first=5,
                name=f"msg_{grupo_id}_{len(grupo_config['mensajes_programados'])}",
                chat_id=grupo_id,
                user_id=grupo_id
            )
        
        await update.message.reply_text(f"✅ Mensaje cada {segundos/60:.0f} minutos")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def add_mensaje_media_grupo(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    
    if update.message.chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ Usa este comando en el grupo.")
        return
    
    grupo_id = update.message.chat_id
    
    try:
        args = update.message.text.split(' ', 1)
        if len(args) < 2:
            await update.message.reply_text("❌ Usa: `/addmedia segundos`")
            return
        
        segundos = float(args[1])
        if segundos < 60:
            await update.message.reply_text("⚠️ Mínimo 60 segundos")
            return
        
        context.user_data['esperando_media'] = segundos
        context.user_data['grupo_id'] = grupo_id
        await update.message.reply_text(f"📤 Envía foto/video para cada {segundos/60:.0f} min")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def remove_mensaje_grupo(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    
    if update.message.chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ Usa este comando en el grupo.")
        return
    
    grupo_id = update.message.chat_id
    grupo_config = get_grupo_config(grupo_id)
    
    try:
        args = update.message.text.split(' ', 1)
        if len(args) < 2:
            await update.message.reply_text("❌ Usa: `/removemsg número`")
            return
        
        num = int(args[1]) - 1
        mensajes = grupo_config.get('mensajes_programados', [])
        
        if 0 <= num < len(mensajes):
            grupo_config['mensajes_programados'].pop(num)
            guardar_grupo_config(grupo_id, grupo_config)
            await update.message.reply_text("✅ Mensaje eliminado")
        else:
            await update.message.reply_text("❌ Número inválido")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def list_mensajes_grupo(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    
    if update.message.chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ Usa este comando en el grupo.")
        return
    
    grupo_id = update.message.chat_id
    grupo_config = get_grupo_config(grupo_id)
    mensajes = grupo_config.get('mensajes_programados', [])
    
    if not mensajes:
        await update.message.reply_text("📨 No hay mensajes.")
        return
    
    texto = "📨 *Mensajes:*\n\n"
    for i, msg in enumerate(mensajes, 1):
        seg = msg.get('intervalo', 3600)
        texto += f"{i}. Cada {seg/60:.0f}min: {msg.get('mensaje', '')[:30]}...\n"
    
    await update.message.reply_text(texto, parse_mode="Markdown")

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
        
        try:
            chat_members = await context.bot.get_chat_administrators(grupo_id)
            user_ids = [m.user.id for m in chat_members]
        except:
            return
        
        if not user_ids:
            return
        
        for msg_config in grupo_config.get('mensajes_programados', []):
            mensaje = msg_config.get('mensaje', '')
            media = msg_config.get('media')
            botones = grupo_config.get('botones_repetidos', [])
            
            for user_id in user_ids:
                try:
                    try:
                        user = await context.bot.get_chat(user_id)
                        nombre = user.first_name or "Usuario"
                    except:
                        nombre = "Usuario"
                    
                    texto = mensaje.replace('{nombre}', nombre)
                    reply_markup = crear_botones(botones)
                    
                    if media and media.get('file_id'):
                        if media.get('tipo') == 'foto':
                            await context.bot.send_photo(
                                chat_id=user_id,
                                photo=media.get('file_id'),
                                caption=texto,
                                parse_mode="Markdown",
                                reply_markup=reply_markup
                            )
                        elif media.get('tipo') == 'video':
                            await context.bot.send_video(
                                chat_id=user_id,
                                video=media.get('file_id'),
                                caption=texto,
                                parse_mode="Markdown",
                                reply_markup=reply_markup
                            )
                    else:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=texto,
                            parse_mode="Markdown",
                            reply_markup=reply_markup
                        )
                    
                    await asyncio.sleep(0.3)
                    
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
        
        await enviar_bienvenida_pv(context, user, grupo_id, es_reingreso)
        
        auto_aprobar = grupo_config.get('auto_aprobar', True)
        tiempo_aprobacion = grupo_config.get('tiempo_aprobacion', 0)
        
        if auto_aprobar:
            if tiempo_aprobacion > 0:
                async def aprobar_despues():
                    await asyncio.sleep(tiempo_aprobacion)
                    try:
                        await context.bot.approve_chat_join_request(chat_id=grupo_id, user_id=user.id)
                    except:
                        pass
                
                asyncio.create_task(aprobar_despues())
            else:
                await context.bot.approve_chat_join_request(chat_id=grupo_id, user_id=user.id)
        else:
            await context.bot.send_message(
                chat_id=ID_ADMIN,
                text=f"❌ Solicitud de {user.first_name} - Pendiente"
            )
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")

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
            
            await asyncio.sleep(1)
            await enviar_despedida_pv(context, user, grupo_id)
            
    except Exception as e:
        logger.error(f"Error en handle_chat_member_update: {str(e)}")

async def enviar_bienvenida_pv(context, user, grupo_id, es_reingreso=False):
    try:
        grupo_config = get_grupo_config(grupo_id)
        config_global = cargar_config()
        
        if es_reingreso:
            mensaje = grupo_config.get('mensaje_reingreso', config_default['mensaje_reingreso'])
            media = grupo_config.get('media_reingreso')
        else:
            mensaje = grupo_config.get('mensaje_bienvenida', config_default['mensaje_bienvenida'])
            media = grupo_config.get('media_bienvenida')
        
        botones = grupo_config.get('botones_bienvenida', [])
        formato = config_global.get('formato_texto', 'markdown')
        proteger = config_global.get('proteger_mensajes', True)
        
        mensaje_personalizado = mensaje.replace('{nombre}', user.first_name)
        mensaje_personalizado = mensaje_personalizado.replace('{mention}', f'@{user.username}' if user.username else user.first_name)
        mensaje_personalizado = mensaje_personalizado.replace('{perfil}', f'[Perfil](tg://user?id={user.id})')
        
        reply_markup = crear_botones(botones)
        
        if media and media.get('file_id'):
            if media.get('tipo') == 'foto':
                msg = await context.bot.send_photo(
                    chat_id=user.id,
                    photo=media.get('file_id'),
                    caption=f"👋 ¡Hola {user.first_name}!\n\n{mensaje_personalizado}",
                    parse_mode=formato.upper(),
                    reply_markup=reply_markup,
                    protect_content=proteger
                )
            elif media.get('tipo') == 'video':
                msg = await context.bot.send_video(
                    chat_id=user.id,
                    video=media.get('file_id'),
                    caption=f"👋 ¡Hola {user.first_name}!\n\n{mensaje_personalizado}",
                    parse_mode=formato.upper(),
                    reply_markup=reply_markup,
                    protect_content=proteger
                )
        else:
            msg = await context.bot.send_message(
                chat_id=user.id,
                text=f"👋 ¡Hola {user.first_name}!\n\n{mensaje_personalizado}",
                parse_mode=formato.upper(),
                reply_markup=reply_markup,
                protect_content=proteger
            )
        
        tiempo_elim = grupo_config.get('tiempo_eliminacion_bienvenida', 0)
        if tiempo_elim > 0:
            if 'mensajes_activos' not in grupo_config:
                grupo_config['mensajes_activos'] = {}
            grupo_config['mensajes_activos'][str(user.id)] = msg.message_id
            guardar_grupo_config(grupo_id, grupo_config)
            
            async def eliminar_bienvenida():
                await asyncio.sleep(tiempo_elim)
                try:
                    await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
                    grupo_config = get_grupo_config(grupo_id)
                    if 'mensajes_activos' in grupo_config:
                        grupo_config['mensajes_activos'].pop(str(user.id), None)
                        guardar_grupo_config(grupo_id, grupo_config)
                except:
                    pass
            
            asyncio.create_task(eliminar_bienvenida())
        
        if config_global.get('borrar_mensajes_pv', True):
            tiempo = config_global.get('tiempo_borrado_pv', 60)
            if tiempo > 0:
                async def borrar_despues():
                    await asyncio.sleep(tiempo)
                    try:
                        await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
                    except:
                        pass
                
                asyncio.create_task(borrar_despues())
        
        return msg
        
    except Exception as e:
        logger.error(f"Error enviando bienvenida: {str(e)}")
        return None

async def enviar_despedida_pv(context, user, grupo_id):
    try:
        grupo_config = get_grupo_config(grupo_id)
        config_global = cargar_config()
        
        mensaje = grupo_config.get('mensaje_despedida', config_default['mensaje_despedida'])
        media = grupo_config.get('media_despedida')
        botones = grupo_config.get('botones_despedida', [])
        formato = config_global.get('formato_texto', 'markdown')
        proteger = config_global.get('proteger_mensajes', True)
        
        mensaje_personalizado = mensaje.replace('{nombre}', user.first_name)
        mensaje_personalizado = mensaje_personalizado.replace('{mention}', f'@{user.username}' if user.username else user.first_name)
        mensaje_personalizado = mensaje_personalizado.replace('{perfil}', f'[Perfil](tg://user?id={user.id})')
        
        reply_markup = crear_botones(botones)
        
        if media and media.get('file_id'):
            if media.get('tipo') == 'foto':
                msg = await context.bot.send_photo(
                    chat_id=user.id,
                    photo=media.get('file_id'),
                    caption=f"👋 ¡Hasta luego {user.first_name}!\n\n{mensaje_personalizado}",
                    parse_mode=formato.upper(),
                    reply_markup=reply_markup,
                    protect_content=proteger
                )
            elif media.get('tipo') == 'video':
                msg = await context.bot.send_video(
                    chat_id=user.id,
                    video=media.get('file_id'),
                    caption=f"👋 ¡Hasta luego {user.first_name}!\n\n{mensaje_personalizado}",
                    parse_mode=formato.upper(),
                    reply_markup=reply_markup,
                    protect_content=proteger
                )
        else:
            msg = await context.bot.send_message(
                chat_id=user.id,
                text=f"👋 ¡Hasta luego {user.first_name}!\n\n{mensaje_personalizado}",
                parse_mode=formato.upper(),
                reply_markup=reply_markup,
                protect_content=proteger
            )
        
        if config_global.get('borrar_mensajes_pv', True):
            tiempo = config_global.get('tiempo_borrado_pv', 60)
            if tiempo > 0:
                async def borrar_despues():
                    await asyncio.sleep(tiempo)
                    try:
                        await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
                    except:
                        pass
                
                asyncio.create_task(borrar_despues())
        
    except Exception as e:
        logger.error(f"Error enviando despedida: {str(e)}")

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
            
            texto = update.message.text
            
            try:
                if accion == 'url':
                    partes_txt = texto.split('|')
                    if len(partes_txt) == 2:
                        grupo_config[lista_key].append({
                            "tipo": "url",
                            "texto": partes_txt[0].strip(),
                            "url": partes_txt[1].strip()
                        })
                        guardar_grupo_config(grupo_id, grupo_config)
                        await update.message.reply_text(f"✅ Botón URL agregado")
                    else:
                        await update.message.reply_text("❌ Formato: `Texto|https://url.com`")
                
                elif accion == 'share':
                    grupo_config[lista_key].append({
                        "tipo": "share",
                        "texto": texto.strip()
                    })
                    guardar_grupo_config(grupo_id, grupo_config)
                    await update.message.reply_text(f"✅ Botón Share agregado")
                
                elif accion == 'alert':
                    partes_txt = texto.split('|')
                    if len(partes_txt) == 2:
                        grupo_config[lista_key].append({
                            "tipo": "alert",
                            "texto": partes_txt[0].strip(),
                            "alert_text": partes_txt[1].strip()
                        })
                        guardar_grupo_config(grupo_id, grupo_config)
                        await update.message.reply_text(f"✅ Botón Alert agregado")
                    else:
                        await update.message.reply_text("❌ Formato: `Texto|Mensaje del popup`")
                
                elif accion == 'edit':
                    partes_txt = texto.split('|')
                    if len(partes_txt) == 2:
                        grupo_config[lista_key].append({
                            "tipo": "edit",
                            "texto": partes_txt[0].strip(),
                            "edit_text": partes_txt[1].strip()
                        })
                        guardar_grupo_config(grupo_id, grupo_config)
                        await update.message.reply_text(f"✅ Botón Edit agregado")
                    else:
                        await update.message.reply_text("❌ Formato: `Texto|Nuevo contenido`")
                
                elif accion == 'delete':
                    grupo_config[lista_key].append({
                        "tipo": "delete",
                        "texto": texto.strip()
                    })
                    guardar_grupo_config(grupo_id, grupo_config)
                    await update.message.reply_text(f"✅ Botón Delete agregado")
                
                elif accion == 'custom':
                    partes_txt = texto.split('|')
                    if len(partes_txt) == 2:
                        grupo_config[lista_key].append({
                            "tipo": "callback",
                            "texto": partes_txt[0].strip(),
                            "callback_data": partes_txt[1].strip()
                        })
                        guardar_grupo_config(grupo_id, grupo_config)
                        await update.message.reply_text(f"✅ Botón Custom agregado")
                    else:
                        await update.message.reply_text("❌ Formato: `Texto|accion`")
                
                elif accion == 'up':
                    try:
                        num = int(texto) - 1
                        if 0 <= num < len(grupo_config[lista_key]) and num > 0:
                            grupo_config[lista_key][num], grupo_config[lista_key][num-1] = grupo_config[lista_key][num-1], grupo_config[lista_key][num]
                            guardar_grupo_config(grupo_id, grupo_config)
                            await update.message.reply_text(f"✅ Botón {num+1} movido hacia arriba")
                        else:
                            await update.message.reply_text("❌ Número inválido")
                    except:
                        await update.message.reply_text("❌ Envía un número válido")
                
                elif accion == 'down':
                    try:
                        num = int(texto) - 1
                        if 0 <= num < len(grupo_config[lista_key]) and num < len(grupo_config[lista_key]) - 1:
                            grupo_config[lista_key][num], grupo_config[lista_key][num+1] = grupo_config[lista_key][num+1], grupo_config[lista_key][num]
                            guardar_grupo_config(grupo_id, grupo_config)
                            await update.message.reply_text(f"✅ Botón {num+1} movido hacia abajo")
                        else:
                            await update.message.reply_text("❌ Número inválido")
                    except:
                        await update.message.reply_text("❌ Envía un número válido")
                
                context.user_data.clear()
                
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {str(e)}")
                context.user_data.clear()
        
        return
    
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

async def handle_media_programada(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    
    segundos = context.user_data.get('esperando_media')
    if not segundos:
        return
    
    grupo_id = context.user_data.get('grupo_id')
    if not grupo_id:
        await update.message.reply_text("❌ Error: no hay grupo configurado.")
        return
    
    grupo_config = get_grupo_config(grupo_id)
    
    if 'mensajes_programados' not in grupo_config:
        grupo_config['mensajes_programados'] = []
    
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        grupo_config['mensajes_programados'].append({
            "intervalo": segundos,
            "mensaje": "¡Hola {nombre}! Recuerda visitar el grupo 🎉",
            "media": {"tipo": "foto", "file_id": file_id}
        })
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text(f"✅ Foto programada cada {segundos/60:.0f} min")
        
        if context.application.job_queue:
            context.application.job_queue.run_repeating(
                enviar_mensaje_programado,
                interval=segundos,
                first=5,
                name=f"msg_{grupo_id}_{len(grupo_config['mensajes_programados'])}",
                chat_id=grupo_id,
                user_id=grupo_id
            )
        
    elif update.message.video:
        file_id = update.message.video.file_id
        grupo_config['mensajes_programados'].append({
            "intervalo": segundos,
            "mensaje": "¡Hola {nombre}! Recuerda visitar el grupo 🎉",
            "media": {"tipo": "video", "file_id": file_id}
        })
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text(f"✅ Video programado cada {segundos/60:.0f} min")
        
        if context.application.job_queue:
            context.application.job_queue.run_repeating(
                enviar_mensaje_programado,
                interval=segundos,
                first=5,
                name=f"msg_{grupo_id}_{len(grupo_config['mensajes_programados'])}",
                chat_id=grupo_id,
                user_id=grupo_id
            )
    else:
        await update.message.reply_text("❌ Envía una foto o video.")
        return
    
    context.user_data.clear()

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

# ==================== INICIO ====================
def main():
    logger.info("🚀 Iniciando Bot Avanzado Pro...")
    
    application = Application.builder().token(TOKEN).build()
    
    # Comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancelar", cancelar))
    
    # Mensajes programados
    application.add_handler(CommandHandler("addmsg", add_mensaje_grupo))
    application.add_handler(CommandHandler("addmedia", add_mensaje_media_grupo))
    application.add_handler(CommandHandler("removemsg", remove_mensaje_grupo))
    application.add_handler(CommandHandler("listmsg", list_mensajes_grupo))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(share_callback, pattern="share_btn"))
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="menu_|welcome_|reingreso_|media_|reset_|auto_|t_|proteger_|borrar_|bt_|elim_|btn_|alert_|edit_|delete_|custom_"))
    
    # Configuración
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_config))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media_programada))
    
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
