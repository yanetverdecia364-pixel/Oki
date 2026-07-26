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
    "mensaje_reingreso": "¡Bienvenido de nuevo {nombre}! 🎉\n\nNos alegra verte otra vez.",
    "mensaje_despedida": "¡Hasta luego {nombre}! 👋\n\nEsperamos verte pronto.",
    "botones": [],
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
    "tiempo_eliminacion_bienvenida": 0,  # 0 = no eliminar, >0 = segundos
    "mensajes_activos": {}  # {user_id: message_id} para eliminar después
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
    
    if str(grupo_id) not in config.get('grupos', {}):
        config['grupos'][str(grupo_id)] = {
            "mensaje_bienvenida": config.get('mensaje_bienvenida', config_default['mensaje_bienvenida']),
            "mensaje_reingreso": config.get('mensaje_reingreso', config_default['mensaje_reingreso']),
            "mensaje_despedida": config.get('mensaje_despedida', config_default['mensaje_despedida']),
            "botones": config.get('botones', []),
            "media_bienvenida": None,
            "media_reingreso": None,
            "media_despedida": None,
            "auto_aprobar": config.get('auto_aprobar', True),
            "tiempo_aprobacion": config.get('tiempo_aprobacion', 0),
            "mensajes_programados": [],
            "tiempo_eliminacion_bienvenida": config.get('tiempo_eliminacion_bienvenida', 0)
        }
        guardar_config(config)
    
    return config['grupos'][str(grupo_id)]

def guardar_grupo_config(grupo_id, grupo_config):
    config = cargar_config()
    config['grupos'][str(grupo_id)] = grupo_config
    guardar_config(config)

# ==================== CREAR BOTONES AVANZADOS ====================

def crear_botones_avanzados(botones_config, grupo_id, user_id=None):
    """Crea botones con diferentes tipos"""
    keyboard = []
    
    for b in botones_config:
        tipo = b.get('tipo', 'url')
        
        if tipo == 'url':
            # Botón URL normal
            keyboard.append([InlineKeyboardButton(b['texto'], url=b['url'])])
        
        elif tipo == 'share':
            # Botón COMPARTIR (solo funciona en grupos)
            keyboard.append([InlineKeyboardButton(
                b['texto'], 
                switch_inline_query="¡Mira este grupo increíble!"
            )])
        
        elif tipo == 'alert':
            # Botón que muestra una ALERTA/POPUP
            keyboard.append([InlineKeyboardButton(
                b['texto'], 
                callback_data=f"alert_{b.get('alert_text', '¡Mensaje importante!')}"
            )])
        
        elif tipo == 'edit':
            # Botón que EDITA el mensaje
            keyboard.append([InlineKeyboardButton(
                b['texto'], 
                callback_data=f"edit_{grupo_id}_{b.get('edit_text', 'Texto editado')}"
            )])
        
        elif tipo == 'delete':
            # Botón que ELIMINA el mensaje
            keyboard.append([InlineKeyboardButton(
                b['texto'], 
                callback_data=f"delete_{grupo_id}"
            )])
        
        elif tipo == 'callback':
            # Botón con acción personalizada
            keyboard.append([InlineKeyboardButton(
                b['texto'], 
                callback_data=f"custom_{b.get('callback_data', 'accion')}"
            )])
    
    return InlineKeyboardMarkup(keyboard) if keyboard else None

# ==================== MENÚ PRINCIPAL ====================

async def menu_principal(update, context, edit=False, grupo_id=None):
    if not grupo_id and update.callback_query:
        grupo_id = update.callback_query.message.chat_id
    elif not grupo_id:
        grupo_id = update.message.chat_id
    
    grupo_config = get_grupo_config(grupo_id)
    tiempo_elim = grupo_config.get('tiempo_eliminacion_bienvenida', 0)
    
    keyboard = [
        [InlineKeyboardButton("📝 Mensaje Bienvenida", callback_data=f"menu_welcome_{grupo_id}")],
        [InlineKeyboardButton("👋 Mensaje Despedida", callback_data=f"menu_goodbye_{grupo_id}")],
        [InlineKeyboardButton("🖼️ Media", callback_data=f"menu_media_{grupo_id}")],
        [InlineKeyboardButton("🔘 Botones Avanzados", callback_data=f"menu_buttons_{grupo_id}")],
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
        f"🗑️ Eliminar bienvenida: {tiempo_elim}s\n\n"
        f"Selecciona una opción:"
    )
    
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            texto,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        await update.callback_query.answer()
    else:
        await update.message.reply_text(
            texto,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

async def start(update, context):
    if update.effective_user.id != ID_ADMIN:
        await update.message.reply_text("❌ No tienes permiso.")
        return
    
    if update.message.chat.type in ['group', 'supergroup']:
        grupo_id = update.message.chat_id
        await menu_principal(update, context, grupo_id=grupo_id)
    else:
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
            await update.message.reply_text(texto, reply_markup=reply_markup)
        else:
            await update.message.reply_text(
                "🤖 *BOT AVANZADO*\n\n"
                "No hay grupos configurados.\n"
                "Agrega el bot a un grupo y usa /start allí."
            )

# ==================== CALLBACKS ====================

async def menu_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ID_ADMIN:
        await query.edit_message_text("❌ No tienes permiso.")
        return
    
    data = query.data
    parts = data.split('_')
    action = parts[0]
    grupo_id = parts[-1] if len(parts) > 2 else None
    
    # Manejar botones de ALERTA
    if action == "alert":
        alert_text = data.replace('alert_', '')
        await query.answer(alert_text, show_alert=True)
        return
    
    # Manejar botones de EDIT
    if action == "edit":
        # parts: edit_grupo_id_texto
        if len(parts) >= 3:
            gid = parts[1]
            edit_text = ' '.join(parts[2:])
            try:
                await query.edit_message_text(
                    f"✏️ *Mensaje editado:*\n\n{edit_text}",
                    parse_mode="Markdown"
                )
                await query.answer("✅ Mensaje editado")
            except Exception as e:
                logger.error(f"Error editando: {str(e)}")
        return
    
    # Manejar botones de DELETE
    if action == "delete":
        try:
            await query.delete_message()
            await query.answer("🗑️ Mensaje eliminado")
        except Exception as e:
            logger.error(f"Error eliminando: {str(e)}")
        return
    
    # Manejar botones CUSTOM
    if action == "custom":
        custom_data = data.replace('custom_', '')
        await query.answer(f"⚡ Acción: {custom_data}")
        return
    
    # Si es listar grupos
    if action == "menu" and parts[1] == "list":
        await listar_grupos(update, context)
        return
    
    # Si es seleccionar grupo
    if action == "menu" and parts[1] == "grupo":
        grupo_id = parts[2]
        await menu_principal(update, context, edit=True, grupo_id=int(grupo_id))
        return
    
    if not grupo_id:
        grupo_id = query.message.chat_id
    
    grupo_id = int(grupo_id)
    grupo_config = get_grupo_config(grupo_id)
    config = cargar_config()
    
    # ---------- ELIMINAR BIENVENIDA ----------
    if action == "menu" and parts[1] == "eliminar":
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
            f"🗑️ *ELIMINAR BIENVENIDA - Grupo {grupo_id}*\n\n"
            f"*Actual:* {tiempo}s\n\n"
            f"Los mensajes de bienvenida se eliminarán después de este tiempo.\n"
            f"0 = No eliminar",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif action == "elim":
        segundos = int(parts[1])
        grupo_config['tiempo_eliminacion_bienvenida'] = segundos
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text(f"✅ Bienvenida se eliminará después de {segundos}s")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
    
    # ---------- MENSAJES ----------
    elif action == "menu" and parts[1] == "welcome":
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
    
    elif action == "menu" and parts[1] == "goodbye":
        await query.edit_message_text(
            "✏️ Envía el mensaje de despedida.\n"
            "Usa `{nombre}`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'despedida'
        context.user_data['grupo_id'] = grupo_id
    
    elif action == "welcome" and parts[1] == "edit":
        await query.edit_message_text(
            "✏️ Envía el mensaje de bienvenida.\n"
            "Usa `{nombre}`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'welcome'
        context.user_data['grupo_id'] = grupo_id
    
    elif action == "reingreso" and parts[1] == "edit":
        await query.edit_message_text(
            "✏️ Envía el mensaje de reingreso.\n"
            "Usa `{nombre}`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'reingreso'
        context.user_data['grupo_id'] = grupo_id
    
    # ---------- MEDIA ----------
    elif action == "menu" and parts[1] == "media":
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
            f"🖼️ *MEDIA - Grupo {grupo_id}*\n\n"
            f"Selecciona una opción:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif action == "media" and parts[1] == "welcome":
        await query.edit_message_text(
            "📤 Envía la foto/video para BIENVENIDA",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'media'
        context.user_data['tipo_media'] = 'bienvenida'
        context.user_data['grupo_id'] = grupo_id
    
    elif action == "media" and parts[1] == "reingreso":
        await query.edit_message_text(
            "📤 Envía la foto/video para REINGRESO",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'media'
        context.user_data['tipo_media'] = 'reingreso'
        context.user_data['grupo_id'] = grupo_id
    
    elif action == "media" and parts[1] == "goodbye":
        await query.edit_message_text(
            "📤 Envía la foto/video para DESPEDIDA",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'media'
        context.user_data['tipo_media'] = 'despedida'
        context.user_data['grupo_id'] = grupo_id
    
    elif action == "media" and parts[1] == "del_welcome":
        grupo_config['media_bienvenida'] = None
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("✅ Media de bienvenida eliminada")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
    
    elif action == "media" and parts[1] == "del_reingreso":
        grupo_config['media_reingreso'] = None
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("✅ Media de reingreso eliminada")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
    
    elif action == "media" and parts[1] == "del_goodbye":
        grupo_config['media_despedida'] = None
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("✅ Media de despedida eliminada")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
    
    # ---------- BOTONES AVANZADOS ----------
    elif action == "menu" and parts[1] == "buttons":
        keyboard = [
            [InlineKeyboardButton("➕ Agregar Botón URL", callback_data=f"btn_url_{grupo_id}")],
            [InlineKeyboardButton("📤 Agregar Botón Share", callback_data=f"btn_share_{grupo_id}")],
            [InlineKeyboardButton("⚠️ Agregar Botón Alert", callback_data=f"btn_alert_{grupo_id}")],
            [InlineKeyboardButton("✏️ Agregar Botón Edit", callback_data=f"btn_edit_{grupo_id}")],
            [InlineKeyboardButton("🗑️ Agregar Botón Delete", callback_data=f"btn_delete_{grupo_id}")],
            [InlineKeyboardButton("⚡ Agregar Botón Custom", callback_data=f"btn_custom_{grupo_id}")],
            [InlineKeyboardButton("🗑️ Eliminar Todos", callback_data=f"btn_clear_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        botones = grupo_config.get('botones', [])
        texto = f"🔘 *BOTONES AVANZADOS - Grupo {grupo_id}*\n\n"
        if botones:
            texto += "*Botones actuales:*\n"
            for i, b in enumerate(botones, 1):
                tipo = b.get('tipo', 'url')
                emoji = {
                    'url': '🔗', 'share': '📤', 'alert': '⚠️', 
                    'edit': '✏️', 'delete': '🗑️', 'callback': '⚡'
                }.get(tipo, '📌')
                texto += f"{i}. {emoji} {b['texto']} ({tipo})\n"
        else:
            texto += "No hay botones configurados.\n"
        
        texto += "\n*Tipos de botones:*\n"
        texto += "• 🔗 URL: Abre un enlace\n"
        texto += "• 📤 Share: Compartir grupo\n"
        texto += "• ⚠️ Alert: Muestra popup\n"
        texto += "• ✏️ Edit: Edita el mensaje\n"
        texto += "• 🗑️ Delete: Elimina el mensaje\n"
        texto += "• ⚡ Custom: Acción personalizada"
        
        await query.edit_message_text(
            texto,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif action == "btn" and parts[1] == "url":
        await query.edit_message_text(
            "🔗 *Agregar Botón URL*\n\n"
            "Envía el botón en formato:\n"
            "`Texto|https://url.com`\n\n"
            "Ejemplo:\n"
            "`📢 Canal|https://t.me/mi_canal`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'btn_url'
        context.user_data['grupo_id'] = grupo_id
    
    elif action == "btn" and parts[1] == "share":
        await query.edit_message_text(
            "📤 *Agregar Botón Share*\n\n"
            "Envía el texto del botón:\n"
            "`Compartir grupo`\n\n"
            "Este botón permite compartir el grupo con otros usuarios.\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'btn_share'
        context.user_data['grupo_id'] = grupo_id
    
    elif action == "btn" and parts[1] == "alert":
        await query.edit_message_text(
            "⚠️ *Agregar Botón Alert*\n\n"
            "Envía en formato:\n"
            "`Texto|Mensaje del popup`\n\n"
            "Ejemplo:\n"
            "`📢 Importante|¡Lee las reglas del grupo!`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'btn_alert'
        context.user_data['grupo_id'] = grupo_id
    
    elif action == "btn" and parts[1] == "edit":
        await query.edit_message_text(
            "✏️ *Agregar Botón Edit*\n\n"
            "Envía en formato:\n"
            "`Texto|Nuevo contenido del mensaje`\n\n"
            "Ejemplo:\n"
            "`📝 Ver más|Este es el nuevo mensaje editado`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'btn_edit'
        context.user_data['grupo_id'] = grupo_id
    
    elif action == "btn" and parts[1] == "delete":
        await query.edit_message_text(
            "🗑️ *Agregar Botón Delete*\n\n"
            "Envía el texto del botón:\n"
            "`Eliminar mensaje`\n\n"
            "Este botón eliminará el mensaje al hacer clic.\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'btn_delete'
        context.user_data['grupo_id'] = grupo_id
    
    elif action == "btn" and parts[1] == "custom":
        await query.edit_message_text(
            "⚡ *Agregar Botón Custom*\n\n"
            "Envía en formato:\n"
            "`Texto|accion_personalizada`\n\n"
            "Ejemplo:\n"
            "`📊 Ver stats|estadisticas`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'btn_custom'
        context.user_data['grupo_id'] = grupo_id
    
    elif action == "btn" and parts[1] == "clear":
        grupo_config['botones'] = []
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("✅ Todos los botones eliminados")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
    
    # ---------- AUTO-APROBACIÓN ----------
    elif action == "menu" and parts[1] == "auto":
        keyboard = [
            [InlineKeyboardButton("✅ Activar", callback_data=f"auto_on_{grupo_id}")],
            [InlineKeyboardButton("❌ Desactivar", callback_data=f"auto_off_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        estado = "ON" if grupo_config.get('auto_aprobar', True) else "OFF"
        await query.edit_message_text(
            f"✅ *AUTO-APROBACIÓN - Grupo {grupo_id}*\n\n"
            f"*Estado:* {estado}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif action == "auto" and parts[1] == "on":
        grupo_config['auto_aprobar'] = True
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("✅ Auto-aprobación ACTIVADA")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
    
    elif action == "auto" and parts[1] == "off":
        grupo_config['auto_aprobar'] = False
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("❌ Auto-aprobación DESACTIVADA")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
    
    # ---------- TIEMPO APROBACIÓN ----------
    elif action == "menu" and parts[1] == "tiempo":
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
            f"⏰ *TIEMPO APROBACIÓN - Grupo {grupo_id}*\n\n"
            f"*Actual:* {tiempo}s",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif action == "t":
        segundos = int(parts[1])
        grupo_config['tiempo_aprobacion'] = segundos
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text(f"✅ Tiempo: {segundos}s")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
    
    # ---------- MENSAJES PROGRAMADOS ----------
    elif action == "menu" and parts[1] == "mensajes":
        await query.edit_message_text(
            "📨 *MENSAJES PROGRAMADOS*\n\n"
            "*Comandos:*\n"
            "/addmsg `segundos|mensaje`\n"
            "/addmedia `segundos` (luego envía foto/video)\n"
            "/removemsg `número`\n"
            "/listmsg - Listar\n\n"
            "*Ejemplo:*\n"
            "`/addmsg 120|¡Hola {nombre}!`",
            parse_mode="Markdown"
        )
    
    # ---------- PROTECCIÓN ----------
    elif action == "menu" and parts[1] == "proteccion":
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
            f"🛡️ *PROTECCIÓN - Grupo {grupo_id}*\n\n"
            f"• Protección: {'ON' if config.get('proteger_mensajes', True) else 'OFF'}\n"
            f"• Borrado PV: {'ON' if config.get('borrar_mensajes_pv', True) else 'OFF'}\n"
            f"• Tiempo: {config.get('tiempo_borrado_pv', 60)}s",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif action == "proteger" and parts[1] == "on":
        config['proteger_mensajes'] = True
        guardar_config(config)
        await query.edit_message_text("✅ Protección ACTIVADA")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
    
    elif action == "proteger" and parts[1] == "off":
        config['proteger_mensajes'] = False
        guardar_config(config)
        await query.edit_message_text("❌ Protección DESACTIVADA")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
    
    elif action == "borrar" and parts[1] == "on":
        config['borrar_mensajes_pv'] = True
        guardar_config(config)
        await query.edit_message_text("✅ Borrado PV ACTIVADO")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
    
    elif action == "borrar" and parts[1] == "off":
        config['borrar_mensajes_pv'] = False
        guardar_config(config)
        await query.edit_message_text("❌ Borrado PV DESACTIVADO")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
    
    elif action == "borrar" and parts[1] == "tiempo":
        keyboard = [
            [InlineKeyboardButton("30s", callback_data=f"bt_30_{grupo_id}")],
            [InlineKeyboardButton("60s", callback_data=f"bt_60_{grupo_id}")],
            [InlineKeyboardButton("120s", callback_data=f"bt_120_{grupo_id}")],
            [InlineKeyboardButton("300s", callback_data=f"bt_300_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_proteccion_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⏰ *Tiempo de borrado:*",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif action == "bt":
        segundos = int(parts[1])
        config['tiempo_borrado_pv'] = segundos
        guardar_config(config)
        await query.edit_message_text(f"✅ Tiempo: {segundos}s")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
    
    # ---------- VISTA PREVIA ----------
    elif action == "menu" and parts[1] == "preview":
        await preview_grupo(update, context, grupo_id)
        await query.delete_message()
    
    # ---------- STATUS ----------
    elif action == "menu" and parts[1] == "status":
        registro = cargar_registro()
        usuarios_grupo = [u for u in registro.get('usuarios', {}).values() if u.get('grupo') == str(grupo_id)]
        
        texto = (
            f"📊 *ESTADO - Grupo {grupo_id}*\n\n"
            f"👥 Usuarios: {len(usuarios_grupo)}\n"
            f"🔘 Botones: {len(grupo_config.get('botones', []))}\n"
            f"📨 Programados: {len(grupo_config.get('mensajes_programados', []))}\n"
            f"🖼️ Media: {'✅' if grupo_config.get('media_bienvenida') else '❌'}\n"
            f"✅ Auto-aprobar: {'ON' if grupo_config.get('auto_aprobar', True) else 'OFF'}"
        )
        keyboard = [[InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
    
    # ---------- RESET ----------
    elif action == "menu" and parts[1] == "reset":
        keyboard = [
            [InlineKeyboardButton("✅ Sí", callback_data=f"reset_confirm_{grupo_id}")],
            [InlineKeyboardButton("❌ No", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"⚠️ *¿RESETEAR Grupo {grupo_id}?*\n"
            "No se puede deshacer.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif action == "reset" and parts[1] == "confirm":
        config = cargar_config()
        config['grupos'][str(grupo_id)] = {
            "mensaje_bienvenida": config_default['mensaje_bienvenida'],
            "mensaje_reingreso": config_default['mensaje_reingreso'],
            "mensaje_despedida": config_default['mensaje_despedida'],
            "botones": [],
            "media_bienvenida": None,
            "media_reingreso": None,
            "media_despedida": None,
            "auto_aprobar": True,
            "tiempo_aprobacion": 0,
            "mensajes_programados": [],
            "tiempo_eliminacion_bienvenida": 0
        }
        guardar_config(config)
        await query.edit_message_text(f"✅ Grupo {grupo_id} reseteado")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
    
    # ---------- ATRÁS ----------
    elif action == "menu" and parts[1] == "back":
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)

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

async def preview_grupo(update, context, grupo_id):
    grupo_config = get_grupo_config(grupo_id)
    mensaje = grupo_config.get('mensaje_bienvenida', 'No configurado')
    botones = grupo_config.get('botones', [])
    media = grupo_config.get('media_bienvenida')
    formato = cargar_config().get('formato_texto', 'markdown')
    
    reply_markup = crear_botones_avanzados(botones, grupo_id)
    
    texto = f"👁️ *Vista previa:*\n\n{mensaje}"
    
    if media and media.get('file_id'):
        if media.get('tipo') == 'foto':
            await update.callback_query.message.reply_photo(
                photo=media.get('file_id'),
                caption=texto,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        elif media.get('tipo') == 'video':
            await update.callback_query.message.reply_video(
                video=media.get('file_id'),
                caption=texto,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
    else:
        await update.callback_query.message.reply_text(
            texto,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

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
                enviar_mensaje_programado_grupo,
                interval=segundos,
                first=10,
                name=f"msg_{grupo_id}_{len(grupo_config['mensajes_programados'])}"
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

async def enviar_mensaje_programado_grupo(context):
    try:
        job_name = context.job.name if hasattr(context, 'job') else None
        if not job_name:
            return
        
        parts = job_name.split('_')
        if len(parts) < 2:
            return
        grupo_id = int(parts[1])
        
        grupo_config = get_grupo_config(grupo_id)
        
        try:
            chat_members = await context.bot.get_chat_administrators(grupo_id)
            user_ids = [m.user.id for m in chat_members]
        except:
            return
        
        for msg_config in grupo_config.get('mensajes_programados', []):
            mensaje = msg_config.get('mensaje', '')
            media = msg_config.get('media')
            
            for user_id in user_ids:
                try:
                    try:
                        user = await context.bot.get_chat(user_id)
                        nombre = user.first_name or "Usuario"
                    except:
                        nombre = "Usuario"
                    
                    texto = mensaje.replace('{nombre}', nombre)
                    
                    if media and media.get('file_id'):
                        if media.get('tipo') == 'foto':
                            await context.bot.send_photo(
                                chat_id=user_id,
                                photo=media.get('file_id'),
                                caption=texto,
                                parse_mode="Markdown"
                            )
                        elif media.get('tipo') == 'video':
                            await context.bot.send_video(
                                chat_id=user_id,
                                video=media.get('file_id'),
                                caption=texto,
                                parse_mode="Markdown"
                            )
                    else:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=texto,
                            parse_mode="Markdown"
                        )
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error: {str(e)}")

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
        
        # Enviar bienvenida y guardar mensaje para eliminación
        msg = await enviar_bienvenida_pv(context, user, grupo_id, es_reingreso)
        
        # Programar eliminación del mensaje
        tiempo_elim = grupo_config.get('tiempo_eliminacion_bienvenida', 0)
        if tiempo_elim > 0 and msg:
            async def eliminar_despues():
                await asyncio.sleep(tiempo_elim)
                try:
                    await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
                    logger.info(f"🗑️ Bienvenida eliminada después de {tiempo_elim}s")
                except Exception as e:
                    logger.error(f"Error eliminando bienvenida: {str(e)}")
            
            asyncio.create_task(eliminar_despues())
        
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
                await context.bot.approve_chat_join_request(chat_id=grupo_id, user_id=user.id)
                logger.info(f"✅ {user.first_name} aprobado inmediatamente")
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
        grupo_id = chat.id
        
        if chat_member.old_chat_member.status not in ['kicked', 'left'] and chat_member.new_chat_member.status in ['kicked', 'left']:
            logger.info(f"👋 {user.first_name} salió del grupo {grupo_id}")
            await enviar_despedida_pv(context, user, grupo_id)
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")

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
        
        botones = grupo_config.get('botones', [])
        formato = config_global.get('formato_texto', 'markdown')
        proteger = config_global.get('proteger_mensajes', True)
        
        mensaje_personalizado = mensaje.replace('{nombre}', user.first_name)
        
        reply_markup = crear_botones_avanzados(botones, grupo_id, user.id)
        
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
        
        logger.info(f"✅ Mensaje enviado a {user.first_name}")
        
        # Programar borrado del mensaje (si está configurado)
        if config_global.get('borrar_mensajes_pv', True):
            tiempo = config_global.get('tiempo_borrado_pv', 60)
            if tiempo > 0:
                async def borrar_despues():
                    await asyncio.sleep(tiempo)
                    try:
                        await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
                        logger.info(f"🗑️ Mensaje borrado de {user.first_name}")
                    except Exception as e:
                        logger.error(f"Error borrando: {str(e)}")
                
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
        formato = config_global.get('formato_texto', 'markdown')
        proteger = config_global.get('proteger_mensajes', True)
        
        mensaje_personalizado = mensaje.replace('{nombre}', user.first_name)
        
        if media and media.get('file_id'):
            if media.get('tipo') == 'foto':
                msg = await context.bot.send_photo(
                    chat_id=user.id,
                    photo=media.get('file_id'),
                    caption=f"👋 ¡Hasta luego {user.first_name}!\n\n{mensaje_personalizado}",
                    parse_mode=formato.upper(),
                    protect_content=proteger
                )
            elif media.get('tipo') == 'video':
                msg = await context.bot.send_video(
                    chat_id=user.id,
                    video=media.get('file_id'),
                    caption=f"👋 ¡Hasta luego {user.first_name}!\n\n{mensaje_personalizado}",
                    parse_mode=formato.upper(),
                    protect_content=proteger
                )
        else:
            msg = await context.bot.send_message(
                chat_id=user.id,
                text=f"👋 ¡Hasta luego {user.first_name}!\n\n{mensaje_personalizado}",
                parse_mode=formato.upper(),
                protect_content=proteger
            )
        
        logger.info(f"✅ Despedida enviada a {user.first_name}")
        
        # Programar borrado de la despedida
        if config_global.get('borrar_mensajes_pv', True):
            tiempo = config_global.get('tiempo_borrado_pv', 60)
            if tiempo > 0:
                async def borrar_despues():
                    await asyncio.sleep(tiempo)
                    try:
                        await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
                        logger.info(f"🗑️ Despedida borrada de {user.first_name}")
                    except Exception as e:
                        logger.error(f"Error borrando: {str(e)}")
                
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
    config_global = cargar_config()
    
    # ---------- MENSAJES ----------
    if estado == 'welcome':
        grupo_config['mensaje_bienvenida'] = update.message.text
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text("✅ Mensaje de bienvenida actualizado.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
    
    elif estado == 'reingreso':
        grupo_config['mensaje_reingreso'] = update.message.text
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text("✅ Mensaje de reingreso actualizado.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
    
    elif estado == 'despedida':
        grupo_config['mensaje_despedida'] = update.message.text
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text("✅ Mensaje de despedida actualizado.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
    
    # ---------- BOTONES AVANZADOS ----------
    elif estado == 'btn_url':
        try:
            partes = update.message.text.split('|')
            if len(partes) == 2:
                if 'botones' not in grupo_config:
                    grupo_config['botones'] = []
                grupo_config['botones'].append({
                    "tipo": "url",
                    "texto": partes[0].strip(),
                    "url": partes[1].strip()
                })
                guardar_grupo_config(grupo_id, grupo_config)
                await update.message.reply_text("✅ Botón URL agregado")
            else:
                await update.message.reply_text("❌ Formato: `Texto|https://url.com`")
            context.user_data.clear()
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    elif estado == 'btn_share':
        try:
            if 'botones' not in grupo_config:
                grupo_config['botones'] = []
            grupo_config['botones'].append({
                "tipo": "share",
                "texto": update.message.text.strip()
            })
            guardar_grupo_config(grupo_id, grupo_config)
            await update.message.reply_text("✅ Botón Share agregado")
            context.user_data.clear()
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    elif estado == 'btn_alert':
        try:
            partes = update.message.text.split('|')
            if len(partes) == 2:
                if 'botones' not in grupo_config:
                    grupo_config['botones'] = []
                grupo_config['botones'].append({
                    "tipo": "alert",
                    "texto": partes[0].strip(),
                    "alert_text": partes[1].strip()
                })
                guardar_grupo_config(grupo_id, grupo_config)
                await update.message.reply_text("✅ Botón Alert agregado")
            else:
                await update.message.reply_text("❌ Formato: `Texto|Mensaje del popup`")
            context.user_data.clear()
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    elif estado == 'btn_edit':
        try:
            partes = update.message.text.split('|')
            if len(partes) == 2:
                if 'botones' not in grupo_config:
                    grupo_config['botones'] = []
                grupo_config['botones'].append({
                    "tipo": "edit",
                    "texto": partes[0].strip(),
                    "edit_text": partes[1].strip()
                })
                guardar_grupo_config(grupo_id, grupo_config)
                await update.message.reply_text("✅ Botón Edit agregado")
            else:
                await update.message.reply_text("❌ Formato: `Texto|Nuevo contenido`")
            context.user_data.clear()
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    elif estado == 'btn_delete':
        try:
            if 'botones' not in grupo_config:
                grupo_config['botones'] = []
            grupo_config['botones'].append({
                "tipo": "delete",
                "texto": update.message.text.strip()
            })
            guardar_grupo_config(grupo_id, grupo_config)
            await update.message.reply_text("✅ Botón Delete agregado")
            context.user_data.clear()
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    elif estado == 'btn_custom':
        try:
            partes = update.message.text.split('|')
            if len(partes) == 2:
                if 'botones' not in grupo_config:
                    grupo_config['botones'] = []
                grupo_config['botones'].append({
                    "tipo": "callback",
                    "texto": partes[0].strip(),
                    "callback_data": partes[1].strip()
                })
                guardar_grupo_config(grupo_id, grupo_config)
                await update.message.reply_text("✅ Botón Custom agregado")
            else:
                await update.message.reply_text("❌ Formato: `Texto|accion`")
            context.user_data.clear()
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    # ---------- MEDIA ----------
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
        
    elif update.message.video:
        file_id = update.message.video.file_id
        grupo_config['mensajes_programados'].append({
            "intervalo": segundos,
            "mensaje": "¡Hola {nombre}! Recuerda visitar el grupo 🎉",
            "media": {"tipo": "video", "file_id": file_id}
        })
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text(f"✅ Video programado cada {segundos/60:.0f} min")
    else:
        await update.message.reply_text("❌ Envía una foto o video.")
        return
    
    context.user_data.clear()

# ==================== BORRAR MENSAJES DEL USUARIO ====================

async def borrar_mensajes_usuario(update, context):
    """Borra los mensajes del usuario en PV instantáneamente"""
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
    
    # Mensajes programados
    application.add_handler(CommandHandler("addmsg", add_mensaje_grupo))
    application.add_handler(CommandHandler("addmedia", add_mensaje_media_grupo))
    application.add_handler(CommandHandler("removemsg", remove_mensaje_grupo))
    application.add_handler(CommandHandler("listmsg", list_mensajes_grupo))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="menu_|welcome_|reingreso_|media_|reset_|auto_|t_|proteger_|borrar_|bt_|elim_|btn_|alert_|edit_|delete_|custom_"))
    
    # Configuración
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_config))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media_programada))
    
    # Borrar mensajes de usuario en PV (INSTANTÁNEO)
    application.add_handler(MessageHandler(filters.ALL & filters.ChatType.PRIVATE, borrar_mensajes_usuario))
    
    # Solicitudes de unión
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    
    # Detectar cuando usuarios salen del grupo
    application.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    
    logger.info("✅ Bot iniciado correctamente!")
    logger.info(f"👤 Admin ID: {ID_ADMIN}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
