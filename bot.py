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
    ChatJoinRequestHandler
)

# ==================== CONFIGURACIÓN ====================
TOKEN = "8960529925:AAGcOZHg8O-oVH_pRJ6CGwLvaRuXpN54lcI"
ID_ADMIN = 5353490913

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ARCHIVO_CONFIG = "config.json"
ARCHIVO_REGISTRO = "registro.json"

config_default = {
    "mensaje_bienvenida": "¡Bienvenido al grupo! 🎉\n\nTe damos la bienvenida a nuestra comunidad.",
    "mensaje_reingreso": "¡Bienvenido de nuevo {nombre}! 🎉\n\nNos alegra verte otra vez.",
    "botones": [
        {"texto": "📢 Canal Oficial", "url": "https://t.me/tucanal"},
        {"texto": "📋 Reglas", "url": "https://t.me/tusreglas"}
    ],
    "media_bienvenida": None,
    "media_reingreso": None,
    "mensajes_programados": [],
    "grupo_id": None,
    "formato_texto": "markdown",
    "auto_aprobar": True,
    "tiempo_aprobacion": 0,
    "borrar_mensajes_pv": True,
    "proteger_mensajes": True,
    "tiempo_borrado_pv": 60,
    "usuarios": {}
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

# ==================== MENÚ PRINCIPAL ====================

async def menu_principal(update, context, edit=False):
    config = cargar_config()
    
    keyboard = [
        [InlineKeyboardButton("📝 Mensaje de Bienvenida", callback_data="menu_welcome")],
        [InlineKeyboardButton("🖼️ Media de Bienvenida", callback_data="menu_media")],
        [InlineKeyboardButton("🔘 Configurar Botones", callback_data="menu_buttons")],
        [InlineKeyboardButton("✅ Auto-Aprobación", callback_data="menu_auto")],
        [InlineKeyboardButton("⏰ Tiempo de Aprobación", callback_data="menu_tiempo")],
        [InlineKeyboardButton("📨 Mensajes Programados", callback_data="menu_mensajes")],
        [InlineKeyboardButton("🎨 Formato de Texto", callback_data="menu_formato")],
        [InlineKeyboardButton("🛡️ Protección PV", callback_data="menu_proteccion")],
        [InlineKeyboardButton("👁️ Vista Previa", callback_data="menu_preview")],
        [InlineKeyboardButton("🔄 Resetear Todo", callback_data="menu_reset")],
        [InlineKeyboardButton("ℹ️ Estado del Bot", callback_data="menu_status")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    texto = (
        f"🤖 *BOT AVANZADO*\n"
        f"{'═' * 25}\n\n"
        f"📌 Selecciona una opción:"
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
    await menu_principal(update, context)

# ==================== CALLBACKS ====================

async def menu_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ID_ADMIN:
        await query.edit_message_text("❌ No tienes permiso.")
        return
    
    data = query.data
    config = cargar_config()
    
    # ---------- PROTECCIÓN PV ----------
    if data == "menu_proteccion":
        keyboard = [
            [InlineKeyboardButton("🔒 Activar Protección", callback_data="proteger_on")],
            [InlineKeyboardButton("🔓 Desactivar Protección", callback_data="proteger_off")],
            [InlineKeyboardButton("🗑️ Borrar PV: ON", callback_data="borrar_on")],
            [InlineKeyboardButton("🗑️ Borrar PV: OFF", callback_data="borrar_off")],
            [InlineKeyboardButton("⏰ Tiempo Borrado", callback_data="borrar_tiempo")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"🛡️ *PROTECCIÓN*\n\n"
            f"• Protección: {'ON' if config.get('proteger_mensajes', True) else 'OFF'}\n"
            f"• Borrado PV: {'ON' if config.get('borrar_mensajes_pv', True) else 'OFF'}\n"
            f"• Tiempo: {config.get('tiempo_borrado_pv', 60)}s",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "proteger_on":
        config['proteger_mensajes'] = True
        guardar_config(config)
        await query.edit_message_text("✅ Protección ACTIVADA")
        await menu_principal(update, context, edit=True)
    
    elif data == "proteger_off":
        config['proteger_mensajes'] = False
        guardar_config(config)
        await query.edit_message_text("❌ Protección DESACTIVADA")
        await menu_principal(update, context, edit=True)
    
    elif data == "borrar_on":
        config['borrar_mensajes_pv'] = True
        guardar_config(config)
        await query.edit_message_text("✅ Borrado PV ACTIVADO")
        await menu_principal(update, context, edit=True)
    
    elif data == "borrar_off":
        config['borrar_mensajes_pv'] = False
        guardar_config(config)
        await query.edit_message_text("❌ Borrado PV DESACTIVADO")
        await menu_principal(update, context, edit=True)
    
    elif data == "borrar_tiempo":
        keyboard = [
            [InlineKeyboardButton("30s", callback_data="bt_30")],
            [InlineKeyboardButton("60s", callback_data="bt_60")],
            [InlineKeyboardButton("120s", callback_data="bt_120")],
            [InlineKeyboardButton("300s", callback_data="bt_300")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_proteccion")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⏰ *Tiempo de borrado:*",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data.startswith("bt_"):
        segundos = int(data.split("_")[1])
        config['tiempo_borrado_pv'] = segundos
        guardar_config(config)
        await query.edit_message_text(f"✅ Tiempo: {segundos}s")
        await menu_principal(update, context, edit=True)
    
    # ---------- AUTO-APROBACIÓN ----------
    elif data == "menu_auto":
        keyboard = [
            [InlineKeyboardButton("✅ Activar", callback_data="auto_on")],
            [InlineKeyboardButton("❌ Desactivar", callback_data="auto_off")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        estado = "ON" if config.get('auto_aprobar', True) else "OFF"
        await query.edit_message_text(
            f"✅ *AUTO-APROBACIÓN*\n\n"
            f"*Estado:* {estado}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "auto_on":
        config['auto_aprobar'] = True
        guardar_config(config)
        await query.edit_message_text("✅ Auto-aprobación ACTIVADA")
        await menu_principal(update, context, edit=True)
    
    elif data == "auto_off":
        config['auto_aprobar'] = False
        guardar_config(config)
        await query.edit_message_text("❌ Auto-aprobación DESACTIVADA")
        await menu_principal(update, context, edit=True)
    
    # ---------- TIEMPO APROBACIÓN ----------
    elif data == "menu_tiempo":
        keyboard = [
            [InlineKeyboardButton("⚡ Inmediata", callback_data="t_0")],
            [InlineKeyboardButton("⏰ 30s", callback_data="t_30")],
            [InlineKeyboardButton("⏰ 60s", callback_data="t_60")],
            [InlineKeyboardButton("⏰ 120s", callback_data="t_120")],
            [InlineKeyboardButton("⏰ 300s", callback_data="t_300")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        tiempo = config.get('tiempo_aprobacion', 0)
        await query.edit_message_text(
            f"⏰ *TIEMPO APROBACIÓN*\n\n"
            f"*Actual:* {tiempo}s",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data.startswith("t_"):
        segundos = int(data.split("_")[1])
        config['tiempo_aprobacion'] = segundos
        guardar_config(config)
        await query.edit_message_text(f"✅ Tiempo: {segundos}s")
        await menu_principal(update, context, edit=True)
    
    # ---------- MENSAJE BIENVENIDA ----------
    elif data == "menu_welcome":
        keyboard = [
            [InlineKeyboardButton("✏️ Editar Bienvenida", callback_data="welcome_edit")],
            [InlineKeyboardButton("✏️ Editar Reingreso", callback_data="reingreso_edit")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📝 *MENSAJES*\n\n"
            "Selecciona qué editar:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "welcome_edit":
        await query.edit_message_text(
            "✏️ Envía el nuevo mensaje de bienvenida.\n"
            "Usa `{nombre}`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'welcome'
    
    elif data == "reingreso_edit":
        await query.edit_message_text(
            "✏️ Envía el mensaje de reingreso.\n"
            "Usa `{nombre}`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'reingreso'
    
    # ---------- MEDIA ----------
    elif data == "menu_media":
        keyboard = [
            [InlineKeyboardButton("📤 Media Bienvenida", callback_data="media_welcome")],
            [InlineKeyboardButton("📤 Media Reingreso", callback_data="media_reingreso")],
            [InlineKeyboardButton("🗑️ Eliminar Bienvenida", callback_data="media_del_welcome")],
            [InlineKeyboardButton("🗑️ Eliminar Reingreso", callback_data="media_del_reingreso")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🖼️ *MEDIA*\n\n"
            "Selecciona una opción:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "media_welcome":
        await query.edit_message_text(
            "📤 Envía la foto/video para BIENVENIDA",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'media'
        context.user_data['tipo_media'] = 'bienvenida'
    
    elif data == "media_reingreso":
        await query.edit_message_text(
            "📤 Envía la foto/video para REINGRESO",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'media'
        context.user_data['tipo_media'] = 'reingreso'
    
    elif data == "media_del_welcome":
        config['media_bienvenida'] = None
        guardar_config(config)
        await query.edit_message_text("✅ Media de bienvenida eliminada")
        await menu_principal(update, context, edit=True)
    
    elif data == "media_del_reingreso":
        config['media_reingreso'] = None
        guardar_config(config)
        await query.edit_message_text("✅ Media de reingreso eliminada")
        await menu_principal(update, context, edit=True)
    
    # ---------- BOTONES ----------
    elif data == "menu_buttons":
        await query.edit_message_text(
            "🔘 *BOTONES*\n\n"
            "Usa /setbuttons para configurar\n"
            "Usa /resetbuttons para eliminar\n\n"
            "*Formato:*\n"
            "`Texto|url, Texto2|url2`\n"
            "`Compartir grupo` - Botón compartir",
            parse_mode="Markdown"
        )
    
    # ---------- MENSAJES PROGRAMADOS ----------
    elif data == "menu_mensajes":
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
    
    # ---------- FORMATO ----------
    elif data == "menu_formato":
        keyboard = [
            [InlineKeyboardButton("📝 Markdown", callback_data="formato_md")],
            [InlineKeyboardButton("🌐 HTML", callback_data="formato_html")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        actual = config.get('formato_texto', 'markdown')
        await query.edit_message_text(
            f"🎨 *FORMATO*\n\n"
            f"*Actual:* {actual}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "formato_md":
        config['formato_texto'] = 'markdown'
        guardar_config(config)
        await query.edit_message_text("✅ Formato: Markdown")
        await menu_principal(update, context, edit=True)
    
    elif data == "formato_html":
        config['formato_texto'] = 'html'
        guardar_config(config)
        await query.edit_message_text("✅ Formato: HTML")
        await menu_principal(update, context, edit=True)
    
    # ---------- VISTA PREVIA ----------
    elif data == "menu_preview":
        await preview(update, context)
        await query.delete_message()
    
    # ---------- RESET ----------
    elif data == "menu_reset":
        keyboard = [
            [InlineKeyboardButton("✅ Sí", callback_data="reset_confirm")],
            [InlineKeyboardButton("❌ No", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⚠️ *¿RESETEAR TODO?*\n"
            "No se puede deshacer.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "reset_confirm":
        guardar_config(config_default)
        guardar_registro({"usuarios": {}})
        await query.edit_message_text("✅ Todo reseteado")
        await menu_principal(update, context, edit=True)
    
    # ---------- STATUS ----------
    elif data == "menu_status":
        registro = cargar_registro()
        texto = (
            f"📊 *ESTADO*\n\n"
            f"👥 Usuarios: {len(registro.get('usuarios', {}))}\n"
            f"🔘 Botones: {len(config.get('botones', []))}\n"
            f"📨 Programados: {len(config.get('mensajes_programados', []))}\n"
            f"🖼️ Media: {'✅' if config.get('media_bienvenida') else '❌'}\n"
            f"✅ Auto-aprobar: {'ON' if config.get('auto_aprobar', True) else 'OFF'}"
        )
        keyboard = [[InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
    
    # ---------- ATRÁS ----------
    elif data == "menu_back":
        await menu_principal(update, context, edit=True)

# ==================== COMANDOS ====================

async def set_welcome(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    await update.message.reply_text(
        "✏️ Envía el mensaje de bienvenida.\n"
        "Usa `{nombre}`\n"
        "Para cancelar: /cancelar",
        parse_mode="Markdown"
    )
    context.user_data['esperando'] = 'welcome'

async def set_buttons(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    await update.message.reply_text(
        "🔘 Envía botones:\n"
        "`Texto|url, Texto2|url2`\n"
        "`Compartir grupo` - Botón compartir\n\n"
        "Ejemplo:\n"
        "`📢 Canal|https://t.me/canal, 📤 Compartir grupo`"
    )
    context.user_data['esperando'] = 'buttons'

async def reset_buttons(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    config = cargar_config()
    config['botones'] = []
    guardar_config(config)
    await update.message.reply_text("✅ Botones eliminados.")

async def preview(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    
    config = cargar_config()
    mensaje = config.get('mensaje_bienvenida', 'No configurado')
    botones = config.get('botones', [])
    media = config.get('media_bienvenida')
    
    keyboard = []
    for b in botones:
        if b.get('texto') in ["Compartir grupo", "📤 Compartir grupo"]:
            keyboard.append([InlineKeyboardButton("📤 Compartir grupo", switch_inline_query="")])
        elif b.get('url'):
            keyboard.append([InlineKeyboardButton(b['texto'], url=b['url'])])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    if media and media.get('file_id'):
        if media.get('tipo') == 'foto':
            await update.message.reply_photo(
                photo=media.get('file_id'),
                caption=f"👁️ *Vista previa:*\n\n{mensaje}",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        elif media.get('tipo') == 'video':
            await update.message.reply_video(
                video=media.get('file_id'),
                caption=f"👁️ *Vista previa:*\n\n{mensaje}",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
    else:
        await update.message.reply_text(
            f"👁️ *Vista previa:*\n\n{mensaje}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

async def reset(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    guardar_config(config_default)
    guardar_registro({"usuarios": {}})
    await update.message.reply_text("✅ Todo reseteado.")

async def status_cmd(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    config = cargar_config()
    registro = cargar_registro()
    await update.message.reply_text(
        f"📊 *Estado*\n\n"
        f"👥 Usuarios: {len(registro.get('usuarios', {}))}\n"
        f"🔘 Botones: {len(config.get('botones', []))}",
        parse_mode="Markdown"
    )

async def cancelar(update, context):
    context.user_data.clear()
    await update.message.reply_text("✅ Cancelado.")

async def set_grupo(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    if update.message.chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ Solo en grupos.")
        return
    config = cargar_config()
    config['grupo_id'] = update.message.chat.id
    guardar_config(config)
    await update.message.reply_text(f"✅ Grupo configurado")

# ==================== MENSAJES PROGRAMADOS ====================

async def add_mensaje(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    
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
        config = cargar_config()
        
        if 'mensajes_programados' not in config:
            config['mensajes_programados'] = []
        
        config['mensajes_programados'].append({
            "intervalo": segundos,
            "mensaje": mensaje,
            "media": None
        })
        guardar_config(config)
        
        # Programar en job_queue
        if context.application.job_queue:
            context.application.job_queue.run_repeating(
                enviar_mensaje_programado,
                interval=segundos,
                first=10,
                name=f"msg_{len(config['mensajes_programados'])}"
            )
        
        await update.message.reply_text(f"✅ Mensaje cada {segundos/60:.0f} minutos")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def add_mensaje_media(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    
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
        await update.message.reply_text(f"📤 Envía foto/video para cada {segundos/60:.0f} min")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def remove_mensaje(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    
    try:
        args = update.message.text.split(' ', 1)
        if len(args) < 2:
            await update.message.reply_text("❌ Usa: `/removemsg número`")
            return
        
        num = int(args[1]) - 1
        config = cargar_config()
        mensajes = config.get('mensajes_programados', [])
        
        if 0 <= num < len(mensajes):
            config['mensajes_programados'].pop(num)
            guardar_config(config)
            await update.message.reply_text("✅ Mensaje eliminado")
        else:
            await update.message.reply_text("❌ Número inválido")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def list_mensajes(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    
    config = cargar_config()
    mensajes = config.get('mensajes_programados', [])
    
    if not mensajes:
        await update.message.reply_text("📨 No hay mensajes.")
        return
    
    texto = "📨 *Mensajes:*\n\n"
    for i, msg in enumerate(mensajes, 1):
        seg = msg.get('intervalo', 3600)
        texto += f"{i}. Cada {seg/60:.0f}min: {msg.get('mensaje', '')[:30]}...\n"
    
    await update.message.reply_text(texto, parse_mode="Markdown")

async def enviar_mensaje_programado(context):
    """Envía mensajes programados"""
    try:
        config = cargar_config()
        grupo_id = config.get('grupo_id')
        
        if not grupo_id:
            return
        
        # Obtener usuarios del grupo
        try:
            chat_members = await context.bot.get_chat_administrators(grupo_id)
            user_ids = [m.user.id for m in chat_members]
        except:
            return
        
        for msg_config in config.get('mensajes_programados', []):
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
        
        logger.info(f"🔵 Solicitud de {user.first_name}")
        
        # Guardar grupo
        config = cargar_config()
        if not config.get('grupo_id'):
            config['grupo_id'] = chat.id
            guardar_config(config)
        
        # Registrar usuario
        registro = cargar_registro()
        user_id = str(user.id)
        
        if user_id not in registro.get('usuarios', {}):
            registro['usuarios'][user_id] = {
                "nombre": user.first_name,
                "username": user.username,
                "veces": 1,
                "fecha": datetime.now().isoformat()
            }
        else:
            registro['usuarios'][user_id]['veces'] += 1
            registro['usuarios'][user_id]['ultima'] = datetime.now().isoformat()
        
        guardar_registro(registro)
        
        # Verificar reingreso
        es_reingreso = registro['usuarios'][user_id]['veces'] > 1
        
        # Enviar bienvenida al PV
        await enviar_bienvenida_pv(context, user, chat, es_reingreso)
        
        # Auto-aprobación
        auto_aprobar = config.get('auto_aprobar', True)
        tiempo_aprobacion = config.get('tiempo_aprobacion', 0)
        
        if auto_aprobar:
            if tiempo_aprobacion > 0:
                # Programar aprobación con el tiempo configurado
                await context.bot.send_message(
                    chat_id=ID_ADMIN,
                    text=f"⏰ {user.first_name} aprobado en {tiempo_aprobacion}s"
                )
                
                # Usar asyncio.sleep en lugar de job_queue (más confiable)
                async def aprobar_despues():
                    await asyncio.sleep(tiempo_aprobacion)
                    try:
                        await context.bot.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
                        logger.info(f"✅ {user.first_name} aprobado después de {tiempo_aprobacion}s")
                    except Exception as e:
                        logger.error(f"Error aprobando: {str(e)}")
                
                # Crear tarea en segundo plano
                asyncio.create_task(aprobar_despues())
                
            else:
                # Aprobación inmediata
                await context.bot.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
                logger.info(f"✅ {user.first_name} aprobado inmediatamente")
        else:
            await context.bot.send_message(
                chat_id=ID_ADMIN,
                text=f"❌ Solicitud de {user.first_name} - Pendiente"
            )
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")

async def enviar_bienvenida_pv(context, user, chat, es_reingreso=False):
    """Envía mensaje de bienvenida al PV"""
    try:
        config = cargar_config()
        
        if es_reingreso:
            mensaje = config.get('mensaje_reingreso', config_default['mensaje_reingreso'])
            media = config.get('media_reingreso')
        else:
            mensaje = config.get('mensaje_bienvenida', config_default['mensaje_bienvenida'])
            media = config.get('media_bienvenida')
        
        botones = config.get('botones', [])
        formato = config.get('formato_texto', 'markdown')
        proteger = config.get('proteger_mensajes', True)
        borrar = config.get('borrar_mensajes_pv', True)
        tiempo_borrado = config.get('tiempo_borrado_pv', 60)
        
        # Personalizar
        mensaje_personalizado = mensaje.replace('{nombre}', user.first_name)
        
        # Botones
        keyboard = []
        for b in botones:
            if b.get('texto') in ["Compartir grupo", "📤 Compartir grupo"]:
                keyboard.append([InlineKeyboardButton("📤 Compartir grupo", switch_inline_query="")])
            elif b.get('url'):
                keyboard.append([InlineKeyboardButton(b['texto'], url=b['url'])])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        # Enviar mensaje
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
        
        # Programar borrado
        if borrar and tiempo_borrado > 0:
            async def borrar_despues():
                await asyncio.sleep(tiempo_borrado)
                try:
                    await context.bot.delete_message(chat_id=user.id, message_id=msg.message_id)
                    logger.info(f"🗑️ Mensaje borrado de {user.first_name}")
                except Exception as e:
                    logger.error(f"Error borrando: {str(e)}")
            
            asyncio.create_task(borrar_despues())
        
    except Exception as e:
        logger.error(f"Error enviando bienvenida: {str(e)}")

# ==================== MANEJO DE CONFIGURACIÓN ====================

async def handle_config(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    
    estado = context.user_data.get('esperando')
    if not estado:
        return
    
    config = cargar_config()
    
    if estado == 'welcome':
        config['mensaje_bienvenida'] = update.message.text
        guardar_config(config)
        await update.message.reply_text("✅ Mensaje de bienvenida actualizado.")
        context.user_data.pop('esperando', None)
        await menu_principal(update, context)
    
    elif estado == 'reingreso':
        config['mensaje_reingreso'] = update.message.text
        guardar_config(config)
        await update.message.reply_text("✅ Mensaje de reingreso actualizado.")
        context.user_data.pop('esperando', None)
        await menu_principal(update, context)
    
    elif estado == 'buttons':
        try:
            nuevos_botones = []
            for item in update.message.text.split(','):
                parte = item.strip().split('|')
                if len(parte) == 2:
                    nuevos_botones.append({
                        "texto": parte[0].strip(),
                        "url": parte[1].strip()
                    })
                elif item.strip() in ["Compartir grupo", "📤 Compartir grupo"]:
                    nuevos_botones.append({
                        "texto": "📤 Compartir grupo",
                        "url": ""
                    })
            
            if nuevos_botones:
                config['botones'] = nuevos_botones
                guardar_config(config)
                await update.message.reply_text(f"✅ {len(nuevos_botones)} botones configurados.")
            else:
                await update.message.reply_text("❌ Formato incorrecto.")
            context.user_data.pop('esperando', None)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    elif estado == 'media':
        tipo = context.user_data.get('tipo_media', 'bienvenida')
        
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            if tipo == 'bienvenida':
                config['media_bienvenida'] = {"tipo": "foto", "file_id": file_id}
            else:
                config['media_reingreso'] = {"tipo": "foto", "file_id": file_id}
            guardar_config(config)
            await update.message.reply_text(f"✅ Foto guardada para {tipo}")
        elif update.message.video:
            file_id = update.message.video.file_id
            if tipo == 'bienvenida':
                config['media_bienvenida'] = {"tipo": "video", "file_id": file_id}
            else:
                config['media_reingreso'] = {"tipo": "video", "file_id": file_id}
            guardar_config(config)
            await update.message.reply_text(f"✅ Video guardado para {tipo}")
        else:
            await update.message.reply_text("❌ Envía una foto o video.")
            return
        
        context.user_data.pop('esperando', None)
        context.user_data.pop('tipo_media', None)

async def handle_media_programada(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    
    segundos = context.user_data.get('esperando_media')
    if not segundos:
        return
    
    config = cargar_config()
    
    if 'mensajes_programados' not in config:
        config['mensajes_programados'] = []
    
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        config['mensajes_programados'].append({
            "intervalo": segundos,
            "mensaje": "¡Hola {nombre}! Recuerda visitar el grupo 🎉",
            "media": {"tipo": "foto", "file_id": file_id}
        })
        guardar_config(config)
        await update.message.reply_text(f"✅ Foto programada cada {segundos/60:.0f} min")
        
    elif update.message.video:
        file_id = update.message.video.file_id
        config['mensajes_programados'].append({
            "intervalo": segundos,
            "mensaje": "¡Hola {nombre}! Recuerda visitar el grupo 🎉",
            "media": {"tipo": "video", "file_id": file_id}
        })
        guardar_config(config)
        await update.message.reply_text(f"✅ Video programado cada {segundos/60:.0f} min")
    else:
        await update.message.reply_text("❌ Envía una foto o video.")
        return
    
    context.user_data.pop('esperando_media', None)

# ==================== BORRAR MENSAJES DEL USUARIO ====================

async def borrar_mensajes_usuario(update, context):
    """Borra los mensajes del usuario en PV"""
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
    except Exception as e:
        logger.error(f"Error borrando mensaje de usuario: {str(e)}")

# ==================== INICIO ====================

def main():
    logger.info("🚀 Iniciando Bot...")
    
    application = Application.builder().token(TOKEN).build()
    
    # Comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setwelcome", set_welcome))
    application.add_handler(CommandHandler("setbuttons", set_buttons))
    application.add_handler(CommandHandler("resetbuttons", reset_buttons))
    application.add_handler(CommandHandler("preview", preview))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("status", status_cmd))
    application.add_handler(CommandHandler("cancelar", cancelar))
    application.add_handler(CommandHandler("setgrupo", set_grupo))
    
    # Mensajes programados
    application.add_handler(CommandHandler("addmsg", add_mensaje))
    application.add_handler(CommandHandler("addmedia", add_mensaje_media))
    application.add_handler(CommandHandler("removemsg", remove_mensaje))
    application.add_handler(CommandHandler("listmsg", list_mensajes))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="menu_|welcome_|reingreso_|media_|formato_|reset_|auto_|t_|proteger_|borrar_|bt_"))
    
    # Configuración
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_config))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media_programada))
    
    # Borrar mensajes de usuario en PV
    application.add_handler(MessageHandler(filters.ALL & filters.ChatType.PRIVATE, borrar_mensajes_usuario))
    
    # Solicitudes de unión
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    
    logger.info("✅ Bot iniciado correctamente!")
    logger.info(f"👤 Admin ID: {ID_ADMIN}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
