import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters, 
    ContextTypes,
    ChatJoinRequestHandler,
    ConversationHandler
)

# ==================== CONFIGURACIÓN ====================
TOKEN = "8960529925:AAGcOZHg8O-oVH_pRJ6CGwLvaRuXpN54lcI"
ID_ADMIN = 5353490913

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ARCHIVO_CONFIG = "config.json"

WAITING_FOR_RESPONSE = 1

config_default = {
    "mensaje_bienvenida": "¡Bienvenido al grupo! 🎉\n\nTe damos la bienvenida a nuestra comunidad.",
    "botones": [
        {"texto": "📢 Canal Oficial", "url": "https://t.me/tucanal"},
        {"texto": "📋 Reglas", "url": "https://t.me/tusreglas"}
    ],
    "media_bienvenida": None,  # {"tipo": "foto" o "video", "file_id": "..."}
    "mensajes_programados": [],
    "grupo_id": None,
    "formato_texto": "markdown",
    "auto_aprobar": True,  # ✅ NUEVO: Activar/Desactivar auto-aprobación
    "tiempo_aprobacion": 0,  # ✅ NUEVO: Tiempo en segundos antes de aprobar (0 = inmediato)
    "solicitudes_pendientes": []  # ✅ NUEVO: Lista de solicitudes pendientes
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

# ==================== MENÚ PRINCIPAL ====================

async def menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    config = cargar_config()
    auto_aprobar = config.get('auto_aprobar', True)
    tiempo = config.get('tiempo_aprobacion', 0)
    
    # Mostrar estado de auto-aprobación
    estado_auto = "✅ Activada" if auto_aprobar else "❌ Desactivada"
    if tiempo > 0:
        minutos = tiempo / 60
        estado_tiempo = f"⏰ Cada {minutos:.0f} min"
    else:
        estado_tiempo = "⚡ Inmediata"
    
    keyboard = [
        [InlineKeyboardButton("📝 Mensaje de Bienvenida", callback_data="menu_welcome")],
        [InlineKeyboardButton("🖼️ Media de Bienvenida", callback_data="menu_media")],
        [InlineKeyboardButton("🔘 Configurar Botones", callback_data="menu_buttons")],
        [InlineKeyboardButton("✅ Auto-Aprobación", callback_data="menu_auto")],
        [InlineKeyboardButton("⏰ Tiempo de Aprobación", callback_data="menu_tiempo")],
        [InlineKeyboardButton("📨 Mensajes Programados", callback_data="menu_mensajes")],
        [InlineKeyboardButton("🎨 Formato de Texto", callback_data="menu_formato")],
        [InlineKeyboardButton("👁️ Vista Previa", callback_data="menu_preview")],
        [InlineKeyboardButton("🔄 Resetear Todo", callback_data="menu_reset")],
        [InlineKeyboardButton("ℹ️ Estado del Bot", callback_data="menu_status")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    texto = (
        f"🤖 *Panel de Control - Bot Avanzado*\n\n"
        f"📌 *Estado:*\n"
        f"• Auto-Aprobación: {estado_auto}\n"
        f"• Tiempo: {estado_tiempo}\n\n"
        f"*Funciones:*\n"
        f"• Mensajes de bienvenida con fotos/videos\n"
        f"• Botones personalizados\n"
        f"• Mensajes automáticos cada minutos\n"
        f"• Envío al PV antes de aprobar\n\n"
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        await update.message.reply_text("❌ No tienes permiso.")
        return
    await menu_principal(update, context)

# ==================== MANEJADOR DE CALLBACKS ====================

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ID_ADMIN:
        await query.edit_message_text("❌ No tienes permiso.")
        return
    
    data = query.data
    config = cargar_config()
    
    # ---------- AUTO-APROBACIÓN ----------
    if data == "menu_auto":
        auto = config.get('auto_aprobar', True)
        
        keyboard = [
            [InlineKeyboardButton("✅ Activar" if not auto else "✅ Ya activada", callback_data="auto_activar")],
            [InlineKeyboardButton("❌ Desactivar" if auto else "❌ Ya desactivada", callback_data="auto_desactivar")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        estado = "✅ Activada" if auto else "❌ Desactivada"
        await query.edit_message_text(
            f"✅ *Auto-Aprobación*\n\n"
            f"*Estado actual:* {estado}\n\n"
            f"Cuando está activada, el bot aprueba automáticamente las solicitudes.\n"
            f"Cuando está desactivada, las solicitudes quedan pendientes.\n\n"
            f"*Nota:* El mensaje de bienvenida siempre se envía al PV.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "auto_activar":
        config['auto_aprobar'] = True
        guardar_config(config)
        await query.edit_message_text("✅ Auto-aprobación ACTIVADA")
        await menu_principal(update, context)
    
    elif data == "auto_desactivar":
        config['auto_aprobar'] = False
        guardar_config(config)
        await query.edit_message_text("❌ Auto-aprobación DESACTIVADA")
        await menu_principal(update, context)
    
    # ---------- TIEMPO DE APROBACIÓN ----------
    elif data == "menu_tiempo":
        tiempo = config.get('tiempo_aprobacion', 0)
        
        keyboard = [
            [InlineKeyboardButton("⚡ Inmediata (0 seg)", callback_data="tiempo_0")],
            [InlineKeyboardButton("⏰ 1 minuto", callback_data="tiempo_60")],
            [InlineKeyboardButton("⏰ 2 minutos", callback_data="tiempo_120")],
            [InlineKeyboardButton("⏰ 5 minutos", callback_data="tiempo_300")],
            [InlineKeyboardButton("⏰ 10 minutos", callback_data="tiempo_600")],
            [InlineKeyboardButton("⏰ 30 minutos", callback_data="tiempo_1800")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if tiempo > 0:
            minutos = tiempo / 60
            texto_tiempo = f"⏰ {minutos:.0f} minutos"
        else:
            texto_tiempo = "⚡ Inmediata"
        
        await query.edit_message_text(
            f"⏰ *Tiempo de Aprobación*\n\n"
            f"*Tiempo actual:* {texto_tiempo}\n\n"
            f"Selecciona cuánto tiempo esperar antes de aprobar:\n"
            f"• *Inmediata:* Aprobar al instante\n"
            f"• *1-30 min:* Esperar antes de aprobar\n\n"
            f"*Importante:* El mensaje de bienvenida se envía en el momento de la solicitud.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data.startswith("tiempo_"):
        segundos = int(data.split("_")[1])
        config['tiempo_aprobacion'] = segundos
        guardar_config(config)
        
        if segundos > 0:
            minutos = segundos / 60
            await query.edit_message_text(f"✅ Tiempo configurado: {minutos:.0f} minutos")
        else:
            await query.edit_message_text("✅ Tiempo configurado: Inmediata")
        await menu_principal(update, context)
    
    # ---------- MENSAJE DE BIENVENIDA ----------
    elif data == "menu_welcome":
        keyboard = [
            [InlineKeyboardButton("✏️ Editar Mensaje", callback_data="welcome_edit")],
            [InlineKeyboardButton("📝 Ver Mensaje Actual", callback_data="welcome_view")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        mensaje_actual = config.get('mensaje_bienvenida', 'No configurado')
        await query.edit_message_text(
            f"📝 *Mensaje de Bienvenida*\n\n"
            f"*Mensaje actual:*\n"
            f"`{mensaje_actual[:100]}...`\n\n"
            f"Usa `{{nombre}}` para mostrar el nombre del usuario.\n"
            f"Ejemplo: `¡Bienvenido {{nombre}}! 🎉`",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "welcome_edit":
        await query.edit_message_text(
            "✏️ Envía el nuevo mensaje de bienvenida.\n\n"
            "Puedes usar:\n"
            "• `*negrita*`\n"
            "• `_cursiva_`\n"
            "• `[texto](url)` para enlaces\n"
            "• `{nombre}` para el nombre del usuario\n\n"
            "Ejemplo:\n"
            "`¡Bienvenido {nombre}! 🎉\n\nVisita nuestro [canal](https://t.me/mi_canal)`\n\n"
            "Para cancelar, escribe /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'welcome'
    
    elif data == "welcome_view":
        mensaje = config.get('mensaje_bienvenida', 'No configurado')
        keyboard = [[InlineKeyboardButton("🔙 Atrás", callback_data="menu_welcome")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📝 *Mensaje actual:*\n\n{mensaje}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    # ---------- MEDIA DE BIENVENIDA ----------
    elif data == "menu_media":
        media = config.get('media_bienvenida')
        
        keyboard = [
            [InlineKeyboardButton("📤 Enviar Foto/Video", callback_data="media_send")],
            [InlineKeyboardButton("🗑️ Eliminar Media", callback_data="media_delete")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        estado = "✅ Configurada" if media else "❌ No configurada"
        tipo = f" ({media.get('tipo')})" if media else ""
        
        await query.edit_message_text(
            f"🖼️ *Media de Bienvenida*\n\n"
            f"*Estado:* {estado}{tipo}\n\n"
            f"Envía una foto o video para usarlo en el mensaje de bienvenida.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "media_send":
        await query.edit_message_text(
            "📤 Envía la **foto** o **video** que quieras usar.\n\n"
            "El bot lo guardará y lo enviará junto al mensaje de bienvenida.\n\n"
            "Para cancelar, escribe /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'media'
    
    elif data == "media_delete":
        config['media_bienvenida'] = None
        guardar_config(config)
        
        keyboard = [[InlineKeyboardButton("🔙 Atrás", callback_data="menu_media")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "✅ Media eliminada correctamente.",
            reply_markup=reply_markup
        )
    
    # ---------- BOTONES ----------
    elif data == "menu_buttons":
        botones = config.get('botones', [])
        
        texto = "🔘 *Configurar Botones*\n\n"
        if botones:
            texto += "*Botones actuales:*\n"
            for i, btn in enumerate(botones, 1):
                if btn.get('url'):
                    texto += f"{i}. {btn['texto']} → {btn['url']}\n"
                else:
                    texto += f"{i}. 📤 {btn['texto']}\n"
        else:
            texto += "No hay botones configurados.\n"
        
        texto += "\n*Comandos:*\n"
        texto += "• /setbuttons - Configurar botones\n"
        texto += "• /resetbuttons - Eliminar todos los botones\n\n"
        texto += "*Formato:*\n"
        texto += "`Texto|url, Texto2|url2`\n"
        texto += "• `Compartir grupo` - Botón para compartir"
        
        keyboard = [[InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
    
    # ---------- MENSAJES PROGRAMADOS ----------
    elif data == "menu_mensajes":
        mensajes = config.get('mensajes_programados', [])
        
        texto = "📨 *Mensajes Programados*\n\n"
        if mensajes:
            texto += "*Mensajes activos:*\n"
            for i, msg in enumerate(mensajes, 1):
                segundos = msg.get('intervalo', 3600)
                if segundos >= 3600:
                    horas = segundos / 3600
                    tiempo = f"{horas:.1f} horas"
                else:
                    minutos = segundos / 60
                    tiempo = f"{minutos:.0f} minutos"
                texto += f"{i}. Cada {tiempo}: {msg.get('mensaje', '')[:40]}...\n"
                if msg.get('media'):
                    texto += "   🖼️ Con media\n"
        else:
            texto += "No hay mensajes programados.\n"
        
        texto += "\n*Comandos:*\n"
        texto += "• /addmsg `segundos|mensaje` - Agregar mensaje\n"
        texto += "• /addmedia `segundos` - Agregar con foto/video\n"
        texto += "• /removemsg `número` - Eliminar mensaje\n"
        texto += "• /listmsg - Listar mensajes\n\n"
        texto += "*Ejemplos:*\n"
        texto += "`/addmsg 120|¡Hola {nombre}! Recuerda participar!` (cada 2 min)\n"
        texto += "`/addmsg 3600|¡Hola {nombre}! Nuevo video!` (cada 1 hora)"
        
        keyboard = [[InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
    
    # ---------- FORMATO DE TEXTO ----------
    elif data == "menu_formato":
        formato = config.get('formato_texto', 'markdown')
        
        keyboard = [
            [InlineKeyboardButton("✅ Markdown" if formato == "markdown" else "📝 Markdown", callback_data="formato_markdown")],
            [InlineKeyboardButton("✅ HTML" if formato == "html" else "🌐 HTML", callback_data="formato_html")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎨 *Formato de Texto*\n\n"
            f"*Formato actual:* `{formato}`\n\n"
            f"Selecciona el formato que prefieras:\n\n"
            f"*Markdown:*\n"
            f"• `*negrita*`\n"
            f"• `_cursiva_`\n"
            f"• `[texto](url)`\n\n"
            f"*HTML:*\n"
            f"• `<b>negrita</b>`\n"
            f"• `<i>cursiva</i>`\n"
            f"• `<a href=\"url\">texto</a>`",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "formato_markdown":
        config['formato_texto'] = 'markdown'
        guardar_config(config)
        await query.edit_message_text("✅ Formato cambiado a Markdown")
        await menu_principal(update, context)
    
    elif data == "formato_html":
        config['formato_texto'] = 'html'
        guardar_config(config)
        await query.edit_message_text("✅ Formato cambiado a HTML")
        await menu_principal(update, context)
    
    # ---------- VISTA PREVIA ----------
    elif data == "menu_preview":
        await preview(update, context)
        await query.delete_message()
    
    # ---------- RESET ----------
    elif data == "menu_reset":
        keyboard = [
            [InlineKeyboardButton("✅ Sí, resetear todo", callback_data="reset_confirm")],
            [InlineKeyboardButton("❌ No, cancelar", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚠️ *¿Estás seguro?*\n\n"
            "Esto eliminará toda la configuración:\n"
            "• Mensaje de bienvenida\n"
            "• Botones\n"
            "• Media\n"
            "• Mensajes programados\n\n"
            "Esta acción no se puede deshacer.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "reset_confirm":
        guardar_config(config_default)
        await query.edit_message_text("✅ Configuración restaurada a valores predeterminados.")
        await menu_principal(update, context)
    
    # ---------- STATUS ----------
    elif data == "menu_status":
        botones = config.get('botones', [])
        mensajes = config.get('mensajes_programados', [])
        media = config.get('media_bienvenida')
        formato = config.get('formato_texto', 'markdown')
        auto_aprobar = config.get('auto_aprobar', True)
        tiempo = config.get('tiempo_aprobacion', 0)
        
        texto = "ℹ️ *Estado del Bot*\n\n"
        texto += f"✅ Bot activo\n"
        texto += f"✅ Auto-Aprobación: {'Activada' if auto_aprobar else 'Desactivada'}\n"
        if tiempo > 0:
            texto += f"⏰ Tiempo: {tiempo/60:.0f} minutos\n"
        else:
            texto += f"⚡ Tiempo: Inmediata\n"
        texto += f"📝 Mensaje: {len(config.get('mensaje_bienvenida', ''))} caracteres\n"
        texto += f"🖼️ Media: {'✅' if media else '❌'}\n"
        texto += f"🔘 Botones: {len(botones)}\n"
        texto += f"📨 Mensajes programados: {len(mensajes)}\n"
        texto += f"🎨 Formato: {formato}\n"
        texto += f"👤 Admin ID: {ID_ADMIN}\n"
        
        if config.get('grupo_id'):
            texto += f"👥 Grupo ID: {config.get('grupo_id')}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
    
    # ---------- BOTÓN ATRÁS ----------
    elif data == "menu_back":
        await menu_principal(update, context)

# ==================== COMANDOS DE CONFIGURACIÓN ====================

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    await update.message.reply_text(
        "✏️ Envía el nuevo mensaje de bienvenida.\n\n"
        "Usa `{nombre}` para mostrar el nombre del usuario.\n"
        "Para cancelar, escribe /cancelar",
        parse_mode="Markdown"
    )
    context.user_data['esperando'] = 'welcome'

async def set_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    await update.message.reply_text(
        "🔘 *Configurar Botones*\n\n"
        "*Formato:*\n"
        "`Texto|url, Texto2|url2`\n\n"
        "*Botón compartir grupo:*\n"
        "Escribe `Compartir grupo`\n\n"
        "*Ejemplo:*\n"
        "`📢 Canal|https://t.me/mi_canal, 📤 Compartir grupo`\n\n"
        "Para cancelar, escribe /cancelar",
        parse_mode="Markdown"
    )
    context.user_data['esperando'] = 'buttons'

async def reset_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    config = cargar_config()
    config['botones'] = []
    guardar_config(config)
    await update.message.reply_text("✅ Todos los botones eliminados.")

async def preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    config = cargar_config()
    mensaje = config.get('mensaje_bienvenida', config_default['mensaje_bienvenida'])
    botones = config.get('botones', config_default['botones'])
    media = config.get('media_bienvenida')
    formato = config.get('formato_texto', 'markdown')
    
    mensaje_personalizado = mensaje.replace('{nombre}', 'Usuario de Prueba')
    
    keyboard = []
    for b in botones:
        if b.get('texto') in ["📤 Compartir grupo", "Compartir grupo"]:
            keyboard.append([InlineKeyboardButton("📤 Compartir grupo", switch_inline_query="")])
        elif b.get('url'):
            keyboard.append([InlineKeyboardButton(b['texto'], url=b['url'])])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    texto_final = f"👁️ *Vista previa:*\n\n{mensaje_personalizado}"
    
    if media and media.get('file_id'):
        if media.get('tipo') == 'foto':
            await update.message.reply_photo(
                photo=media.get('file_id'),
                caption=texto_final,
                parse_mode=formato.upper(),
                reply_markup=reply_markup
            )
        elif media.get('tipo') == 'video':
            await update.message.reply_video(
                video=media.get('file_id'),
                caption=texto_final,
                parse_mode=formato.upper(),
                reply_markup=reply_markup
            )
    else:
        await update.message.reply_text(
            texto_final,
            parse_mode=formato.upper(),
            reply_markup=reply_markup
        )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    guardar_config(config_default)
    await update.message.reply_text("✅ Configuración restaurada.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    config = cargar_config()
    botones = config.get('botones', [])
    mensajes = config.get('mensajes_programados', [])
    media = config.get('media_bienvenida')
    
    await update.message.reply_text(
        f"ℹ️ *Estado*\n\n"
        f"✅ Bot activo\n"
        f"📝 {len(config.get('mensaje_bienvenida', ''))} caracteres\n"
        f"🖼️ Media: {'✅' if media else '❌'}\n"
        f"🔘 {len(botones)} botones\n"
        f"📨 {len(mensajes)} mensajes programados",
        parse_mode="Markdown"
    )

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('esperando', None)
    context.user_data.pop('esperando_media', None)
    await update.message.reply_text("✅ Operación cancelada.")

async def set_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    if not update.message.chat.type in ['group', 'supergroup']:
        await update.message.reply_text("❌ Este comando solo funciona en grupos.")
        return
    
    config = cargar_config()
    config['grupo_id'] = update.message.chat.id
    guardar_config(config)
    
    await update.message.reply_text(f"✅ Grupo configurado correctamente.\nID: {update.message.chat.id}")

# ==================== MENSAJES PROGRAMADOS ====================

async def add_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    try:
        args = update.message.text.split(' ', 1)
        if len(args) < 2:
            await update.message.reply_text(
                "❌ Usa: `/addmsg segundos|mensaje`\n"
                "Ejemplo: `/addmsg 120|¡Hola {nombre}!` (cada 2 minutos)",
                parse_mode="Markdown"
            )
            return
        
        partes = args[1].split('|', 1)
        if len(partes) != 2:
            await update.message.reply_text("❌ Formato incorrecto. Usa: `segundos|mensaje`")
            return
        
        segundos = float(partes[0])
        mensaje = partes[1]
        
        if segundos < 60:
            await update.message.reply_text("⚠️ El mínimo es 60 segundos (1 minuto)")
            return
        
        config = cargar_config()
        if 'mensajes_programados' not in config:
            config['mensajes_programados'] = []
        
        config['mensajes_programados'].append({
            "intervalo": segundos,
            "mensaje": mensaje,
            "media": None
        })
        guardar_config(config)
        
        if segundos >= 3600:
            horas = segundos / 3600
            await update.message.reply_text(f"✅ Mensaje programado cada {horas:.1f} horas")
        else:
            minutos = segundos / 60
            await update.message.reply_text(f"✅ Mensaje programado cada {minutos:.0f} minutos")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def add_mensaje_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    try:
        args = update.message.text.split(' ', 1)
        if len(args) < 2:
            await update.message.reply_text(
                "❌ Usa: `/addmedia segundos`\n"
                "Luego envía la foto o video",
                parse_mode="Markdown"
            )
            return
        
        segundos = float(args[1])
        if segundos < 60:
            await update.message.reply_text("⚠️ El mínimo es 60 segundos (1 minuto)")
            return
        
        context.user_data['esperando_media'] = segundos
        
        if segundos >= 3600:
            horas = segundos / 3600
            await update.message.reply_text(f"📤 Envía la foto o video para el mensaje programado cada {horas:.1f} horas")
        else:
            minutos = segundos / 60
            await update.message.reply_text(f"📤 Envía la foto o video para el mensaje programado cada {minutos:.0f} minutos")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def remove_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    try:
        args = update.message.text.split(' ', 1)
        if len(args) < 2:
            await update.message.reply_text("❌ Usa: `/removemsg número`")
            return
        
        num = int(args[1]) - 1
        config = cargar_config()
        
        if 0 <= num < len(config.get('mensajes_programados', [])):
            eliminado = config['mensajes_programados'].pop(num)
            guardar_config(config)
            await update.message.reply_text(f"✅ Mensaje eliminado: {eliminado.get('mensaje', '')[:30]}...")
        else:
            await update.message.reply_text("❌ Número inválido")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def list_mensajes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    config = cargar_config()
    mensajes = config.get('mensajes_programados', [])
    
    if not mensajes:
        await update.message.reply_text("📨 No hay mensajes programados.")
        return
    
    texto = "📨 *Mensajes Programados:*\n\n"
    for i, msg in enumerate(mensajes, 1):
        segundos = msg.get('intervalo', 3600)
        if segundos >= 3600:
            horas = segundos / 3600
            tiempo = f"{horas:.1f} horas"
        else:
            minutos = segundos / 60
            tiempo = f"{minutos:.0f} minutos"
        texto += f"{i}. Cada {tiempo}: {msg.get('mensaje', '')[:50]}...\n"
        if msg.get('media'):
            texto += "   🖼️ Con media\n"
    
    await update.message.reply_text(texto, parse_mode="Markdown")

async def enviar_mensaje_programado(context: ContextTypes.DEFAULT_TYPE):
    """Envía mensajes programados a todos los miembros del grupo"""
    try:
        config = cargar_config()
        grupo_id = config.get('grupo_id')
        
        if not grupo_id:
            logger.warning("No hay grupo configurado")
            return
        
        try:
            chat_members = await context.bot.get_chat_administrators(grupo_id)
            user_ids = [member.user.id for member in chat_members]
        except:
            logger.warning("No se pueden obtener miembros")
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
                    
                    texto_personalizado = mensaje.replace('{nombre}', nombre)
                    
                    if media and media.get('file_id'):
                        if media.get('tipo') == 'foto':
                            await context.bot.send_photo(
                                chat_id=user_id,
                                photo=media.get('file_id'),
                                caption=texto_personalizado,
                                parse_mode="Markdown"
                            )
                        elif media.get('tipo') == 'video':
                            await context.bot.send_video(
                                chat_id=user_id,
                                video=media.get('file_id'),
                                caption=texto_personalizado,
                                parse_mode="Markdown"
                            )
                    else:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=texto_personalizado,
                            parse_mode="Markdown"
                        )
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error enviando a {user_id}: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error en enviar_mensaje_programado: {str(e)}")

async def programar_mensajes(application: Application):
    config = cargar_config()
    
    for msg_config in config.get('mensajes_programados', []):
        intervalo = msg_config.get('intervalo', 3600)
        application.job_queue.run_repeating(
            enviar_mensaje_programado,
            interval=intervalo,
            first=10,
            name="mensaje_programado"
        )
        if intervalo >= 3600:
            horas = intervalo / 3600
            logger.info(f"📨 Mensaje programado cada {horas:.1f} horas")
        else:
            minutos = intervalo / 60
            logger.info(f"📨 Mensaje programado cada {minutos:.0f} minutos")

# ==================== SOLICITUDES DE UNIÓN (CORREGIDO) ====================

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja las solicitudes de unión a grupos"""
    try:
        if not update.chat_join_request:
            return
            
        join_request = update.chat_join_request
        user = join_request.from_user
        chat = join_request.chat
        
        logger.info(f"🔵 Nueva solicitud de {user.first_name} (@{user.username})")
        
        # Guardar ID del grupo
        config = cargar_config()
        if not config.get('grupo_id'):
            config['grupo_id'] = chat.id
            guardar_config(config)
            logger.info(f"📌 Grupo guardado: {chat.title} (ID: {chat.id})")
        
        # ✅ ENVIAR MENSAJE DE BIENVENIDA AL PV ANTES DE APROBAR
        await enviar_bienvenida_pv(update, context, user, chat)
        
        # Verificar auto-aprobación
        auto_aprobar = config.get('auto_aprobar', True)
        tiempo_aprobacion = config.get('tiempo_aprobacion', 0)
        
        if auto_aprobar:
            if tiempo_aprobacion > 0:
                # ✅ Aprobar después del tiempo configurado
                logger.info(f"⏰ Esperando {tiempo_aprobacion} segundos para aprobar a {user.first_name}")
                
                # Programar aprobación
                context.application.job_queue.run_once(
                    aprobar_solicitud,
                    tiempo_aprobacion,
                    chat_id=chat.id,
                    user_id=user.id,
                    name=f"aprobar_{user.id}"
                )
                
                # Enviar mensaje al admin
                await context.bot.send_message(
                    chat_id=ID_ADMIN,
                    text=f"⏰ Solicitud de {user.first_name} será aprobada en {tiempo_aprobacion/60:.0f} minutos"
                )
            else:
                # ✅ Aprobación inmediata
                await aprobar_solicitud(context, chat_id=chat.id, user_id=user.id)
        else:
            # ❌ No aprobar automáticamente
            logger.info(f"❌ Auto-aprobación desactivada para {user.first_name}")
            await context.bot.send_message(
                chat_id=ID_ADMIN,
                text=f"❌ Nueva solicitud de {user.first_name} (@{user.username})\n"
                     f"Pendiente de aprobación manual."
            )
        
        return WAITING_FOR_RESPONSE
        
    except Exception as e:
        logger.error(f"Error en handle_join_request: {str(e)}")
        return None

async def enviar_bienvenida_pv(update: Update, context: ContextTypes.DEFAULT_TYPE, user, chat):
    """Envía el mensaje de bienvenida al PV del usuario"""
    try:
        config = cargar_config()
        
        mensaje = config.get('mensaje_bienvenida', config_default['mensaje_bienvenida'])
        botones = config.get('botones', config_default['botones'])
        media = config.get('media_bienvenida')
        formato = config.get('formato_texto', 'markdown')
        
        # Personalizar mensaje
        mensaje_personalizado = mensaje.replace('{nombre}', user.first_name)
        
        # Crear botones
        keyboard = []
        for b in botones:
            if b.get('texto') in ["📤 Compartir grupo", "Compartir grupo"]:
                keyboard.append([InlineKeyboardButton("📤 Compartir grupo", switch_inline_query="")])
            elif b.get('url'):
                keyboard.append([InlineKeyboardButton(b['texto'], url=b['url'])])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        # ✅ ENVIAR mensaje de bienvenida al PV
        if media and media.get('file_id'):
            if media.get('tipo') == 'foto':
                await context.bot.send_photo(
                    chat_id=user.id,
                    photo=media.get('file_id'),
                    caption=f"👋 ¡Hola {user.first_name}!\n\n{mensaje_personalizado}",
                    parse_mode=formato.upper(),
                    reply_markup=reply_markup
                )
            elif media.get('tipo') == 'video':
                await context.bot.send_video(
                    chat_id=user.id,
                    video=media.get('file_id'),
                    caption=f"👋 ¡Hola {user.first_name}!\n\n{mensaje_personalizado}",
                    parse_mode=formato.upper(),
                    reply_markup=reply_markup
                )
        else:
            await context.bot.send_message(
                chat_id=user.id,
                text=f"👋 ¡Hola {user.first_name}!\n\n{mensaje_personalizado}",
                parse_mode=formato.upper(),
                reply_markup=reply_markup
            )
        
        logger.info(f"✅ Bienvenida enviada al PV de {user.first_name}")
        
    except Exception as e:
        logger.error(f"Error enviando bienvenida a {user.first_name}: {str(e)}")

async def aprobar_solicitud(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int):
    """Aprueba la solicitud de unión"""
    try:
        await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
        logger.info(f"✅ Solicitud aprobada para usuario {user_id}")
        
        # Notificar al admin
        await context.bot.send_message(
            chat_id=ID_ADMIN,
            text=f"✅ Usuario {user_id} aprobado automáticamente."
        )
        
    except Exception as e:
        logger.error(f"Error aprobando solicitud: {str(e)}")

async def handle_user_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la respuesta del usuario después de unirse"""
    try:
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        logger.info(f"💬 Respuesta de {user_name}: {update.message.text[:50]}...")
        
        await update.message.reply_text(
            f"✅ Gracias por tu respuesta, {user_name}!",
            parse_mode="Markdown"
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error en handle_user_response: {str(e)}")
        return ConversationHandler.END

# ==================== MANEJO DE CONFIGURACIÓN ====================

async def handle_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    estado = context.user_data.get('esperando')
    if not estado:
        return
    
    config = cargar_config()
    
    if estado == 'welcome':
        config['mensaje_bienvenida'] = update.message.text
        guardar_config(config)
        await update.message.reply_text("✅ Mensaje actualizado.")
        context.user_data.pop('esperando', None)
        
        keyboard = [[InlineKeyboardButton("🔙 Atrás", callback_data="menu_welcome")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ Configuración guardada", reply_markup=reply_markup)
    
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
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            config['media_bienvenida'] = {"tipo": "foto", "file_id": file_id}
            guardar_config(config)
            await update.message.reply_text("✅ Foto guardada para la bienvenida.")
            context.user_data.pop('esperando', None)
        elif update.message.video:
            file_id = update.message.video.file_id
            config['media_bienvenida'] = {"tipo": "video", "file_id": file_id}
            guardar_config(config)
            await update.message.reply_text("✅ Video guardado para la bienvenida.")
            context.user_data.pop('esperando', None)
        else:
            await update.message.reply_text("❌ Envía una foto o video.")

async def handle_media_programada(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        if segundos >= 3600:
            horas = segundos / 3600
            await update.message.reply_text(f"✅ Mensaje con foto programado cada {horas:.1f} horas")
        else:
            minutos = segundos / 60
            await update.message.reply_text(f"✅ Mensaje con foto programado cada {minutos:.0f} minutos")
        
    elif update.message.video:
        file_id = update.message.video.file_id
        config['mensajes_programados'].append({
            "intervalo": segundos,
            "mensaje": "¡Hola {nombre}! Recuerda visitar el grupo 🎉",
            "media": {"tipo": "video", "file_id": file_id}
        })
        guardar_config(config)
        
        if segundos >= 3600:
            horas = segundos / 3600
            await update.message.reply_text(f"✅ Mensaje con video programado cada {horas:.1f} horas")
        else:
            minutos = segundos / 60
            await update.message.reply_text(f"✅ Mensaje con video programado cada {minutos:.0f} minutos")
    else:
        await update.message.reply_text("❌ Envía una foto o video.")
        return
    
    context.user_data.pop('esperando_media', None)

# ==================== INICIO ====================

def main():
    logger.info("🚀 Iniciando bot avanzado...")
    
    application = Application.builder().token(TOKEN).build()
    
    # ---------- COMANDOS DEL ADMIN ----------
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setwelcome", set_welcome))
    application.add_handler(CommandHandler("setbuttons", set_buttons))
    application.add_handler(CommandHandler("resetbuttons", reset_buttons))
    application.add_handler(CommandHandler("preview", preview))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("cancelar", cancelar))
    application.add_handler(CommandHandler("setgrupo", set_grupo))
    
    # ---------- MENSAJES PROGRAMADOS ----------
    application.add_handler(CommandHandler("addmsg", add_mensaje))
    application.add_handler(CommandHandler("addmedia", add_mensaje_media))
    application.add_handler(CommandHandler("removemsg", remove_mensaje))
    application.add_handler(CommandHandler("listmsg", list_mensajes))
    
    # ---------- CALLBACKS DEL MENÚ ----------
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="menu_|welcome_|media_|formato_|reset_|auto_|tiempo_"))
    
    # ---------- CONFIGURACIÓN ----------
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_config))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media_programada))
    
    # ---------- SOLICITUDES DE UNIÓN ----------
    conv_handler = ConversationHandler(
        entry_points=[ChatJoinRequestHandler(handle_join_request)],
        states={
            WAITING_FOR_RESPONSE: [
                MessageHandler(
                    filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
                    handle_user_response
                )
            ]
        },
        fallbacks=[],
        per_chat=False,
        name="join_request_conversation"
    )
    application.add_handler(conv_handler)
    
    # ---------- INICIAR MENSAJES PROGRAMADOS ----------
    if application.job_queue:
        config = cargar_config()
        for msg_config in config.get('mensajes_programados', []):
            intervalo = msg_config.get('intervalo', 3600)
            application.job_queue.run_repeating(
                enviar_mensaje_programado,
                interval=intervalo,
                first=10,
                name="mensaje_programado"
            )
            if intervalo >= 3600:
                horas = intervalo / 3600
                logger.info(f"📨 Mensaje programado cada {horas:.1f} horas")
            else:
                minutos = intervalo / 60
                logger.info(f"📨 Mensaje programado cada {minutos:.0f} minutos")
    else:
        logger.warning("⚠️ JobQueue no disponible")
    
    logger.info("✅ Bot avanzado iniciado correctamente!")
    logger.info(f"👤 Admin ID: {ID_ADMIN}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
