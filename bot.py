import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ARCHIVO_CONFIG = "config.json"
ARCHIVO_REGISTRO = "registro.json"

# Estados
WAITING_FOR_RESPONSE = 1
WAITING_MEDIA = 2

config_default = {
    "mensaje_bienvenida": "¡Bienvenido al grupo! 🎉\n\nTe damos la bienvenida a nuestra comunidad.",
    "mensaje_reingreso": "¡Bienvenido de nuevo {nombre}! 🎉\n\nNos alegra verte otra vez.",
    "botones": [
        {"texto": "📢 Canal Oficial", "url": "https://t.me/tucanal", "color": "primary"},
        {"texto": "📋 Reglas", "url": "https://t.me/tusreglas", "color": "secondary"}
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
    "usuarios_registrados": {}
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

# ==================== MENÚ PRINCIPAL ESTÉTICO ====================

async def menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    config = cargar_config()
    auto_aprobar = config.get('auto_aprobar', True)
    tiempo = config.get('tiempo_aprobacion', 0)
    proteger = config.get('proteger_mensajes', True)
    
    estado_auto = "✅ Activada" if auto_aprobar else "❌ Desactivada"
    estado_proteger = "🔒 Activado" if proteger else "🔓 Desactivado"
    if tiempo > 0:
        minutos = tiempo / 60
        estado_tiempo = f"⏰ {minutos:.0f} min"
    else:
        estado_tiempo = "⚡ Inmediata"
    
    keyboard = [
        [InlineKeyboardButton("📝 ✨ Mensaje de Bienvenida", callback_data="menu_welcome")],
        [InlineKeyboardButton("🖼️ 🎬 Media de Bienvenida", callback_data="menu_media")],
        [InlineKeyboardButton("🔘 🎨 Botones Colores", callback_data="menu_buttons")],
        [InlineKeyboardButton("✅ 🔄 Auto-Aprobación", callback_data="menu_auto")],
        [InlineKeyboardButton("⏰ ⏳ Tiempo de Aprobación", callback_data="menu_tiempo")],
        [InlineKeyboardButton("📨 🔁 Mensajes Programados", callback_data="menu_mensajes")],
        [InlineKeyboardButton("🎨 📝 Formato de Texto", callback_data="menu_formato")],
        [InlineKeyboardButton("🔒 🛡️ Protección PV", callback_data="menu_proteccion")],
        [InlineKeyboardButton("👁️ 🖼️ Vista Previa", callback_data="menu_preview")],
        [InlineKeyboardButton("🔄 ❌ Resetear Todo", callback_data="menu_reset")],
        [InlineKeyboardButton("ℹ️ 📊 Estado del Bot", callback_data="menu_status")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    texto = (
        f"🤖 *✨ BOT AVANZADO PRO ✨*\n"
        f"{'═' * 30}\n\n"
        f"📌 *ESTADO:*\n"
        f"• Auto-Aprobación: {estado_auto}\n"
        f"• Tiempo: {estado_tiempo}\n"
        f"• Protección PV: {estado_proteger}\n\n"
        f"📋 *FUNCIONES:*\n"
        f"✅ Mensajes con Fotos/Videos\n"
        f"✅ Botones con Colores\n"
        f"✅ Mensajes Programados\n"
        f"✅ Borrado Automático PV\n"
        f"✅ Protección de Mensajes\n"
        f"✅ Mensaje de Reingreso\n\n"
        f"🔽 *Selecciona una opción:*"
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
    
    # ---------- PROTECCIÓN PV ----------
    if data == "menu_proteccion":
        proteger = config.get('proteger_mensajes', True)
        borrar = config.get('borrar_mensajes_pv', True)
        tiempo_borrado = config.get('tiempo_borrado_pv', 60)
        
        keyboard = [
            [InlineKeyboardButton("🔒 Activar Protección" if not proteger else "🔒 Ya Activada", callback_data="proteger_activar")],
            [InlineKeyboardButton("🔓 Desactivar Protección" if proteger else "🔓 Ya Desactivada", callback_data="proteger_desactivar")],
            [InlineKeyboardButton("🗑️ Borrar Mensajes PV" if borrar else "🗑️ No Borrar", callback_data="borrar_toggle")],
            [InlineKeyboardButton(f"⏰ Tiempo: {tiempo_borrado}s", callback_data="borrar_tiempo")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        estado = "🔒 Activada" if proteger else "🔓 Desactivada"
        estado_borrar = "✅ Activo" if borrar else "❌ Inactivo"
        
        await query.edit_message_text(
            f"🛡️ *PROTECCIÓN Y PRIVACIDAD*\n\n"
            f"*Protección de mensajes:* {estado}\n"
            f"  ↳ Impide reenviar mensajes del bot\n\n"
            f"*Borrado automático PV:* {estado_borrar}\n"
            f"  ↳ Tiempo: {tiempo_borrado} segundos\n\n"
            f"*Funciones:*\n"
            f"• Los mensajes del bot no se pueden reenviar\n"
            f"• Los mensajes en PV se borran automáticamente\n"
            f"• Los mensajes del usuario también se borran",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "proteger_activar":
        config['proteger_mensajes'] = True
        guardar_config(config)
        await query.edit_message_text("✅ Protección de mensajes ACTIVADA")
        await menu_principal(update, context)
    
    elif data == "proteger_desactivar":
        config['proteger_mensajes'] = False
        guardar_config(config)
        await query.edit_message_text("❌ Protección de mensajes DESACTIVADA")
        await menu_principal(update, context)
    
    elif data == "borrar_toggle":
        config['borrar_mensajes_pv'] = not config.get('borrar_mensajes_pv', True)
        guardar_config(config)
        estado = "ACTIVADO" if config['borrar_mensajes_pv'] else "DESACTIVADO"
        await query.edit_message_text(f"✅ Borrado automático {estADO}")
        await menu_principal(update, context)
    
    elif data == "borrar_tiempo":
        keyboard = [
            [InlineKeyboardButton("30 segundos", callback_data="borrar_30")],
            [InlineKeyboardButton("60 segundos", callback_data="borrar_60")],
            [InlineKeyboardButton("120 segundos", callback_data="borrar_120")],
            [InlineKeyboardButton("300 segundos (5 min)", callback_data="borrar_300")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_proteccion")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⏰ *Selecciona el tiempo de borrado:*\n\n"
            "Los mensajes en PV se borrarán después de este tiempo.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data.startswith("borrar_"):
        segundos = int(data.split("_")[1])
        config['tiempo_borrado_pv'] = segundos
        guardar_config(config)
        await query.edit_message_text(f"✅ Tiempo configurado: {segundos} segundos")
        await menu_principal(update, context)
    
    # ---------- AUTO-APROBACIÓN ----------
    elif data == "menu_auto":
        auto = config.get('auto_aprobar', True)
        
        keyboard = [
            [InlineKeyboardButton("✅ Activar" if not auto else "✅ Ya Activada", callback_data="auto_activar")],
            [InlineKeyboardButton("❌ Desactivar" if auto else "❌ Ya Desactivada", callback_data="auto_desactivar")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        estado = "✅ Activada" if auto else "❌ Desactivada"
        await query.edit_message_text(
            f"✅ *AUTO-APROBACIÓN*\n\n"
            f"*Estado:* {estado}\n\n"
            f"• *Activada:* Aprueba automáticamente\n"
            f"• *Desactivada:* Queda pendiente\n\n"
            f"*El mensaje de bienvenida SIEMPRE se envía al PV*",
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
        keyboard = [
            [InlineKeyboardButton("⚡ Inmediata (0s)", callback_data="tiempo_0")],
            [InlineKeyboardButton("⏰ 30 segundos", callback_data="tiempo_30")],
            [InlineKeyboardButton("⏰ 1 minuto", callback_data="tiempo_60")],
            [InlineKeyboardButton("⏰ 2 minutos", callback_data="tiempo_120")],
            [InlineKeyboardButton("⏰ 5 minutos", callback_data="tiempo_300")],
            [InlineKeyboardButton("⏰ 10 minutos", callback_data="tiempo_600")],
            [InlineKeyboardButton("⏰ 30 minutos", callback_data="tiempo_1800")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        tiempo = config.get('tiempo_aprobacion', 0)
        if tiempo > 0:
            if tiempo >= 60:
                minutos = tiempo / 60
                texto_tiempo = f"⏰ {minutos:.0f} minutos"
            else:
                texto_tiempo = f"⏰ {tiempo} segundos"
        else:
            texto_tiempo = "⚡ Inmediata"
        
        await query.edit_message_text(
            f"⏰ *TIEMPO DE APROBACIÓN*\n\n"
            f"*Actual:* {texto_tiempo}\n\n"
            f"Selecciona el tiempo de espera antes de aprobar.\n"
            f"*El mensaje de bienvenida se envía al momento.*",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data.startswith("tiempo_"):
        segundos = int(data.split("_")[1])
        config['tiempo_aprobacion'] = segundos
        guardar_config(config)
        
        if segundos > 0:
            if segundos >= 60:
                minutos = segundos / 60
                await query.edit_message_text(f"✅ Tiempo: {minutos:.0f} minutos")
            else:
                await query.edit_message_text(f"✅ Tiempo: {segundos} segundos")
        else:
            await query.edit_message_text("✅ Tiempo: Inmediata")
        await menu_principal(update, context)
    
    # ---------- MENSAJE DE BIENVENIDA ----------
    elif data == "menu_welcome":
        keyboard = [
            [InlineKeyboardButton("✏️ Editar Bienvenida", callback_data="welcome_edit")],
            [InlineKeyboardButton("✏️ Editar Reingreso", callback_data="welcome_reingreso")],
            [InlineKeyboardButton("📝 Ver Mensaje", callback_data="welcome_view")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        mensaje = config.get('mensaje_bienvenida', 'No configurado')
        reingreso = config.get('mensaje_reingreso', 'No configurado')
        
        await query.edit_message_text(
            f"📝 *MENSAJES DE BIENVENIDA*\n\n"
            f"*Bienvenida:*\n`{mensaje[:60]}...`\n\n"
            f"*Reingreso:*\n`{reingreso[:60]}...`\n\n"
            f"Usa `{{nombre}}` para el nombre del usuario.\n"
            f"Usa `{{membresia}}` para días en el grupo.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "welcome_edit":
        await query.edit_message_text(
            "✏️ *EDITAR BIENVENIDA*\n\n"
            "Envía el nuevo mensaje de bienvenida.\n\n"
            "Variables disponibles:\n"
            "• `{nombre}` - Nombre del usuario\n"
            "• `{membresia}` - Días en el grupo\n\n"
            "Formato:\n"
            "• `*negrita*` - Negrita\n"
            "• `_cursiva_` - Cursiva\n"
            "• `[texto](url)` - Enlace\n\n"
            "Ejemplo:\n"
            "`¡Bienvenido {nombre}! 🎉`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'welcome'
    
    elif data == "welcome_reingreso":
        await query.edit_message_text(
            "✏️ *EDITAR MENSAJE DE REINGRESO*\n\n"
            "Envía el mensaje para usuarios que vuelven a unirse.\n\n"
            "Variables disponibles:\n"
            "• `{nombre}` - Nombre del usuario\n"
            "• `{membresia}` - Días en el grupo\n\n"
            "Ejemplo:\n"
            "`¡Bienvenido de nuevo {nombre}! 🎉`\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'reingreso'
    
    elif data == "welcome_view":
        mensaje = config.get('mensaje_bienvenida', 'No configurado')
        reingreso = config.get('mensaje_reingreso', 'No configurado')
        keyboard = [[InlineKeyboardButton("🔙 Atrás", callback_data="menu_welcome")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📝 *MENSAJES COMPLETOS*\n\n"
            f"*Bienvenida:*\n{mensaje}\n\n"
            f"*Reingreso:*\n{reingreso}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    # ---------- MEDIA ----------
    elif data == "menu_media":
        media = config.get('media_bienvenida')
        media_reingreso = config.get('media_reingreso')
        
        keyboard = [
            [InlineKeyboardButton("📤 Bienvenida", callback_data="media_send")],
            [InlineKeyboardButton("📤 Reingreso", callback_data="media_send_reingreso")],
            [InlineKeyboardButton("🗑️ Eliminar Bienvenida", callback_data="media_delete")],
            [InlineKeyboardButton("🗑️ Eliminar Reingreso", callback_data="media_delete_reingreso")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        estado1 = "✅" if media else "❌"
        estado2 = "✅" if media_reingreso else "❌"
        
        await query.edit_message_text(
            f"🖼️ *MEDIA DE BIENVENIDA*\n\n"
            f"*Bienvenida:* {estado1}\n"
            f"*Reingreso:* {estado2}\n\n"
            f"Envía una foto o video para cada mensaje.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "media_send":
        await query.edit_message_text(
            "📤 Envía la foto/video para la **BIENVENIDA**\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'media'
        context.user_data['tipo_media'] = 'bienvenida'
    
    elif data == "media_send_reingreso":
        await query.edit_message_text(
            "📤 Envía la foto/video para el **REINGRESO**\n\n"
            "Para cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'media'
        context.user_data['tipo_media'] = 'reingreso'
    
    elif data == "media_delete":
        config['media_bienvenida'] = None
        guardar_config(config)
        await query.edit_message_text("✅ Media de bienvenida eliminada")
        await menu_principal(update, context)
    
    elif data == "media_delete_reingreso":
        config['media_reingreso'] = None
        guardar_config(config)
        await query.edit_message_text("✅ Media de reingreso eliminada")
        await menu_principal(update, context)
    
    # ---------- BOTONES CON COLORES ----------
    elif data == "menu_buttons":
        botones = config.get('botones', [])
        
        texto = "🎨 *BOTONES CON COLORES*\n\n"
        if botones:
            texto += "*Botones actuales:*\n"
            for i, btn in enumerate(botones, 1):
                color = btn.get('color', 'primary')
                emoji = {
                    'primary': '🔵',
                    'secondary': '⚪',
                    'success': '🟢',
                    'danger': '🔴',
                    'warning': '🟡'
                }.get(color, '🔵')
                texto += f"{i}. {emoji} {btn['texto']}\n"
        else:
            texto += "No hay botones configurados.\n"
        
        texto += "\n*Comandos:*\n"
        texto += "/setbuttons - Configurar botones\n"
        texto += "/resetbuttons - Eliminar todos\n\n"
        texto += "*Formato:*\n"
        texto += "`Texto|url|color`\n"
        texto += "• Colores: primary, secondary, success, danger, warning\n"
        texto += "• `Compartir grupo` - Botón compartir\n\n"
        texto += "*Ejemplo:*\n"
        texto += "`📢 Canal|https://t.me/canal|primary, 📤 Compartir grupo`"
        
        keyboard = [[InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
    
    # ---------- MENSAJES PROGRAMADOS ----------
    elif data == "menu_mensajes":
        mensajes = config.get('mensajes_programados', [])
        
        texto = "📨 *MENSAJES PROGRAMADOS*\n\n"
        if mensajes:
            texto += "*Activos:*\n"
            for i, msg in enumerate(mensajes, 1):
                segundos = msg.get('intervalo', 3600)
                if segundos >= 3600:
                    horas = segundos / 3600
                    tiempo = f"{horas:.1f}h"
                else:
                    minutos = segundos / 60
                    tiempo = f"{minutos:.0f}min"
                texto += f"{i}. Cada {tiempo}: {msg.get('mensaje', '')[:30]}...\n"
                if msg.get('media'):
                    texto += "   🖼️ Con media\n"
        else:
            texto += "No hay mensajes programados.\n"
        
        texto += "\n*Comandos:*\n"
        texto += "/addmsg `segundos|mensaje`\n"
        texto += "/addmedia `segundos`\n"
        texto += "/removemsg `número`\n"
        texto += "/listmsg - Listar\n\n"
        texto += "*Ejemplo:*\n"
        texto += "`/addmsg 120|¡Hola {nombre}!` (cada 2 min)"
        
        keyboard = [[InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
    
    # ---------- FORMATO ----------
    elif data == "menu_formato":
        formato = config.get('formato_texto', 'markdown')
        
        keyboard = [
            [InlineKeyboardButton("✅ Markdown" if formato == "markdown" else "📝 Markdown", callback_data="formato_markdown")],
            [InlineKeyboardButton("✅ HTML" if formato == "html" else "🌐 HTML", callback_data="formato_html")],
            [InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎨 *FORMATO DE TEXTO*\n\n"
            f"*Actual:* `{formato}`\n\n"
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
        await query.edit_message_text("✅ Formato: Markdown")
        await menu_principal(update, context)
    
    elif data == "formato_html":
        config['formato_texto'] = 'html'
        guardar_config(config)
        await query.edit_message_text("✅ Formato: HTML")
        await menu_principal(update, context)
    
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
            "⚠️ *¿RESETEAR TODO?*\n\n"
            "Esto eliminará TODA la configuración.\n"
            "No se puede deshacer.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "reset_confirm":
        guardar_config(config_default)
        # Borrar registro
        with open(ARCHIVO_REGISTRO, "w") as f:
            json.dump({"usuarios": {}}, f)
        await query.edit_message_text("✅ Todo reseteado correctamente.")
        await menu_principal(update, context)
    
    # ---------- STATUS ----------
    elif data == "menu_status":
        botones = config.get('botones', [])
        mensajes = config.get('mensajes_programados', [])
        media = config.get('media_bienvenida')
        registro = cargar_registro()
        usuarios = registro.get('usuarios', {})
        
        texto = "📊 *ESTADO DEL BOT*\n\n"
        texto += f"✅ Bot activo\n"
        texto += f"👥 Usuarios registrados: {len(usuarios)}\n"
        texto += f"📝 Mensaje: {len(config.get('mensaje_bienvenida', ''))} caracteres\n"
        texto += f"🖼️ Media: {'✅' if media else '❌'}\n"
        texto += f"🔘 Botones: {len(botones)}\n"
        texto += f"📨 Programados: {len(mensajes)}\n"
        texto += f"🎨 Formato: {config.get('formato_texto', 'markdown')}\n"
        texto += f"✅ Auto-aprobar: {'✅' if config.get('auto_aprobar', True) else '❌'}\n"
        texto += f"🔒 Protección: {'✅' if config.get('proteger_mensajes', True) else '❌'}"
        
        keyboard = [[InlineKeyboardButton("🔙 Atrás", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
    
    # ---------- ATRÁS ----------
    elif data == "menu_back":
        await menu_principal(update, context)

# ==================== COMANDOS ====================

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    await update.message.reply_text(
        "✏️ Envía el mensaje de bienvenida.\n\n"
        "Usa `{nombre}` para el nombre.\n"
        "Para cancelar: /cancelar",
        parse_mode="Markdown"
    )
    context.user_data['esperando'] = 'welcome'

async def set_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    await update.message.reply_text(
        "🎨 *Configurar Botones con Colores*\n\n"
        "*Formato:*\n"
        "`Texto|url|color`\n\n"
        "*Colores:*\n"
        "🔵 primary, ⚪ secondary, 🟢 success, 🔴 danger, 🟡 warning\n\n"
        "*Botón Compartir:* `Compartir grupo`\n\n"
        "*Ejemplo:*\n"
        "`📢 Canal|https://t.me/canal|primary, 📤 Compartir grupo`\n\n"
        "Para cancelar: /cancelar",
        parse_mode="Markdown"
    )
    context.user_data['esperando'] = 'buttons'

async def reset_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    config = cargar_config()
    config['botones'] = []
    guardar_config(config)
    await update.message.reply_text("✅ Botones eliminados.")

async def preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    config = cargar_config()
    mensaje = config.get('mensaje_bienvenida', config_default['mensaje_bienvenida'])
    botones = config.get('botones', config_default['botones'])
    media = config.get('media_bienvenida')
    formato = config.get('formato_texto', 'markdown')
    
    mensaje_personalizado = mensaje.replace('{nombre}', 'Usuario')
    
    keyboard = []
    for b in botones:
        if b.get('texto') in ["Compartir grupo", "📤 Compartir grupo"]:
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
    with open(ARCHIVO_REGISTRO, "w") as f:
        json.dump({"usuarios": {}}, f)
    await update.message.reply_text("✅ Todo reseteado.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    config = cargar_config()
    registro = cargar_registro()
    await update.message.reply_text(
        f"📊 *Estado*\n\n"
        f"✅ Bot activo\n"
        f"👥 Usuarios: {len(registro.get('usuarios', {}))}\n"
        f"📝 Mensaje: {len(config.get('mensaje_bienvenida', ''))} caracteres\n"
        f"🔘 Botones: {len(config.get('botones', []))}",
        parse_mode="Markdown"
    )

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("✅ Operación cancelada.")

async def set_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    if update.message.chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ Solo en grupos.")
        return
    
    config = cargar_config()
    config['grupo_id'] = update.message.chat.id
    guardar_config(config)
    await update.message.reply_text(f"✅ Grupo configurado ID: {update.message.chat.id}")

# ==================== MENSAJES PROGRAMADOS ====================

async def add_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    try:
        args = update.message.text.split(' ', 1)
        if len(args) < 2:
            await update.message.reply_text(
                "❌ Usa: `/addmsg segundos|mensaje`\n"
                "Ejemplo: `/addmsg 120|¡Hola {nombre}!`",
                parse_mode="Markdown"
            )
            return
        
        partes = args[1].split('|', 1)
        if len(partes) != 2:
            await update.message.reply_text("❌ Formato: `segundos|mensaje`")
            return
        
        segundos = float(partes[0])
        mensaje = partes[1]
        
        if segundos < 60:
            await update.message.reply_text("⚠️ Mínimo 60 segundos")
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
            await update.message.reply_text(f"✅ Mensaje cada {segundos/3600:.1f} horas")
        else:
            await update.message.reply_text(f"✅ Mensaje cada {segundos/60:.0f} minutos")
        
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
                "Luego envía la foto/video",
                parse_mode="Markdown"
            )
            return
        
        segundos = float(args[1])
        if segundos < 60:
            await update.message.reply_text("⚠️ Mínimo 60 segundos")
            return
        
        context.user_data['esperando_media'] = segundos
        await update.message.reply_text(f"📤 Envía la foto/video para cada {segundos/60:.0f} minutos")
        
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
            await update.message.reply_text(f"✅ Eliminado: {eliminado.get('mensaje', '')[:30]}...")
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
    
    texto = "📨 *Mensajes:*\n\n"
    for i, msg in enumerate(mensajes, 1):
        segundos = msg.get('intervalo', 3600)
        if segundos >= 3600:
            tiempo = f"{segundos/3600:.1f}h"
        else:
            tiempo = f"{segundos/60:.0f}min"
        texto += f"{i}. Cada {tiempo}: {msg.get('mensaje', '')[:40]}...\n"
        if msg.get('media'):
            texto += "   🖼️ Con media\n"
    
    await update.message.reply_text(texto, parse_mode="Markdown")

async def enviar_mensaje_programado(context: ContextTypes.DEFAULT_TYPE):
    """Envía mensajes programados"""
    try:
        config = cargar_config()
        grupo_id = config.get('grupo_id')
        
        if not grupo_id:
            return
        
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
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error enviando a {user_id}: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error en enviar_mensaje_programado: {str(e)}")

# ==================== SOLICITUDES DE UNIÓN ====================

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja solicitudes de unión"""
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
                "fecha": datetime.now().isoformat(),
                "veces": 1
            }
        else:
            registro['usuarios'][user_id]['veces'] += 1
            registro['usuarios'][user_id]['ultima'] = datetime.now().isoformat()
        
        guardar_registro(registro)
        
        # Verificar si es reingreso
        es_reingreso = registro['usuarios'][user_id]['veces'] > 1
        
        # ENVIAR MENSAJE AL PV
        await enviar_bienvenida_pv(update, context, user, chat, es_reingreso)
        
        # Auto-aprobación
        auto_aprobar = config.get('auto_aprobar', True)
        tiempo_aprobacion = config.get('tiempo_aprobacion', 0)
        
        if auto_aprobar:
            if tiempo_aprobacion > 0:
                # Programar aprobación
                context.application.job_queue.run_once(
                    aprobar_solicitud,
                    tiempo_aprobacion,
                    chat_id=chat.id,
                    user_id=user.id
                )
                await context.bot.send_message(
                    chat_id=ID_ADMIN,
                    text=f"⏰ {user.first_name} aprobado en {tiempo_aprobacion}s"
                )
            else:
                await aprobar_solicitud(context, chat_id=chat.id, user_id=user.id)
        else:
            await context.bot.send_message(
                chat_id=ID_ADMIN,
                text=f"❌ Solicitud de {user.first_name} - Pendiente"
            )
        
        return WAITING_FOR_RESPONSE
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return None

async def enviar_bienvenida_pv(update: Update, context: ContextTypes.DEFAULT_TYPE, user, chat, es_reingreso=False):
    """Envía mensaje de bienvenida al PV"""
    try:
        config = cargar_config()
        
        if es_reingreso:
            mensaje = config.get('mensaje_reingreso', config_default['mensaje_reingreso'])
            media = config.get('media_reingreso')
        else:
            mensaje = config.get('mensaje_bienvenida', config_default['mensaje_bienvenida'])
            media = config.get('media_bienvenida')
        
        botones = config.get('botones', config_default['botones'])
        formato = config.get('formato_texto', 'markdown')
        
        # Personalizar
        mensaje_personalizado = mensaje.replace('{nombre}', user.first_name)
        
        # Crear botones
        keyboard = []
        for b in botones:
            if b.get('texto') in ["Compartir grupo", "📤 Compartir grupo"]:
                keyboard.append([InlineKeyboardButton("📤 Compartir grupo", switch_inline_query="")])
            elif b.get('url'):
                keyboard.append([InlineKeyboardButton(b['texto'], url=b['url'])])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        # Mensaje con protección
        if media and media.get('file_id'):
            if media.get('tipo') == 'foto':
                msg = await context.bot.send_photo(
                    chat_id=user.id,
                    photo=media.get('file_id'),
                    caption=f"👋 ¡Hola {user.first_name}!\n\n{mensaje_personalizado}",
                    parse_mode=formato.upper(),
                    reply_markup=reply_markup,
                    protect_content=config.get('proteger_mensajes', True)
                )
            elif media.get('tipo') == 'video':
                msg = await context.bot.send_video(
                    chat_id=user.id,
                    video=media.get('file_id'),
                    caption=f"👋 ¡Hola {user.first_name}!\n\n{mensaje_personalizado}",
                    parse_mode=formato.upper(),
                    reply_markup=reply_markup,
                    protect_content=config.get('proteger_mensajes', True)
                )
        else:
            msg = await context.bot.send_message(
                chat_id=user.id,
                text=f"👋 ¡Hola {user.first_name}!\n\n{mensaje_personalizado}",
                parse_mode=formato.upper(),
                reply_markup=reply_markup,
                protect_content=config.get('proteger_mensajes', True)
            )
        
        logger.info(f"✅ Mensaje enviado a {user.first_name}")
        
        # Programar borrado si está activado
        if config.get('borrar_mensajes_pv', True):
            tiempo = config.get('tiempo_borrado_pv', 60)
            if tiempo > 0:
                context.application.job_queue.run_once(
                    borrar_mensaje,
                    tiempo,
                    chat_id=user.id,
                    message_id=msg.message_id
                )
        
    except Exception as e:
        logger.error(f"Error enviando bienvenida: {str(e)}")

async def aprobar_solicitud(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int):
    """Aprueba solicitud"""
    try:
        await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
        logger.info(f"✅ Usuario {user_id} aprobado")
    except Exception as e:
        logger.error(f"Error aprobando: {str(e)}")

async def borrar_mensaje(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    """Borra un mensaje después de cierto tiempo"""
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"🗑️ Mensaje {message_id} borrado en {chat_id}")
    except Exception as e:
        logger.error(f"Error borrando mensaje: {str(e)}")

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
        await update.message.reply_text("✅ Mensaje de bienvenida actualizado.")
        context.user_data.pop('esperando', None)
    
    elif estado == 'reingreso':
        config['mensaje_reingreso'] = update.message.text
        guardar_config(config)
        await update.message.reply_text("✅ Mensaje de reingreso actualizado.")
        context.user_data.pop('esperando', None)
    
    elif estado == 'buttons':
        try:
            nuevos_botones = []
            for item in update.message.text.split(','):
                parte = [p.strip() for p in item.strip().split('|')]
                
                if len(parte) == 3:
                    nuevos_botones.append({
                        "texto": parte[0],
                        "url": parte[1],
                        "color": parte[2]
                    })
                elif len(parte) == 2:
                    nuevos_botones.append({
                        "texto": parte[0],
                        "url": parte[1],
                        "color": "primary"
                    })
                elif item.strip() in ["Compartir grupo", "📤 Compartir grupo"]:
                    nuevos_botones.append({
                        "texto": "📤 Compartir grupo",
                        "url": "",
                        "color": "success"
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
        tipo_media = context.user_data.get('tipo_media', 'bienvenida')
        
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            if tipo_media == 'bienvenida':
                config['media_bienvenida'] = {"tipo": "foto", "file_id": file_id}
            else:
                config['media_reingreso'] = {"tipo": "foto", "file_id": file_id}
            guardar_config(config)
            await update.message.reply_text(f"✅ Foto guardada para {tipo_media}.")
        elif update.message.video:
            file_id = update.message.video.file_id
            if tipo_media == 'bienvenida':
                config['media_bienvenida'] = {"tipo": "video", "file_id": file_id}
            else:
                config['media_reingreso'] = {"tipo": "video", "file_id": file_id}
            guardar_config(config)
            await update.message.reply_text(f"✅ Video guardado para {tipo_media}.")
        else:
            await update.message.reply_text("❌ Envía una foto o video.")
            return
        
        context.user_data.pop('esperando', None)
        context.user_data.pop('tipo_media', None)

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

async def borrar_mensajes_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Borra los mensajes del usuario en PV"""
    if update.effective_user.id != ID_ADMIN:
        return
    
    if update.message.chat.type != 'private':
        return
    
    config = cargar_config()
    if not config.get('borrar_mensajes_pv', True):
        return
    
    try:
        # Borrar el mensaje del usuario
        await context.bot.delete_message(
            chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
        logger.info(f"🗑️ Mensaje de usuario borrado")
    except Exception as e:
        logger.error(f"Error borrando mensaje de usuario: {str(e)}")

# ==================== INICIO ====================

def main():
    logger.info("🚀 Iniciando Bot Avanzado Pro...")
    
    application = Application.builder().token(TOKEN).build()
    
    # Comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setwelcome", set_welcome))
    application.add_handler(CommandHandler("setbuttons", set_buttons))
    application.add_handler(CommandHandler("resetbuttons", reset_buttons))
    application.add_handler(CommandHandler("preview", preview))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("cancelar", cancelar))
    application.add_handler(CommandHandler("setgrupo", set_grupo))
    
    # Mensajes programados
    application.add_handler(CommandHandler("addmsg", add_mensaje))
    application.add_handler(CommandHandler("addmedia", add_mensaje_media))
    application.add_handler(CommandHandler("removemsg", remove_mensaje))
    application.add_handler(CommandHandler("listmsg", list_mensajes))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="menu_|welcome_|media_|formato_|reset_|auto_|tiempo_|proteger_|borrar_"))
    
    # Configuración
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_config))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media_programada))
    
    # Borrar mensajes de usuarios en PV
    application.add_handler(MessageHandler(filters.ALL & filters.ChatType.PRIVATE, borrar_mensajes_usuario))
    
    # Solicitudes de unión
    conv_handler = ConversationHandler(
        entry_points=[ChatJoinRequestHandler(handle_join_request)],
        states={},
        fallbacks=[],
        per_chat=False,
        name="join_request"
    )
    application.add_handler(conv_handler)
    
    # Job Queue
    if application.job_queue:
        config = cargar_config()
        for msg in config.get('mensajes_programados', []):
            intervalo = msg.get('intervalo', 3600)
            application.job_queue.run_repeating(
                enviar_mensaje_programado,
                interval=intervalo,
                first=10,
                name="mensaje_programado"
            )
    else:
        logger.warning("⚠️ JobQueue no disponible")
    
    logger.info("✅ Bot iniciado correctamente!")
    logger.info(f"👤 Admin ID: {ID_ADMIN}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
