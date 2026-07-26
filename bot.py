import os
import json
import logging
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Verificar versión de Python
if sys.version_info >= (3, 13):
    print("⚠️  Usando Python 3.13 o superior - aplicando parche...")
    # Parche para evitar el error
    from telegram.ext._updater import Updater
    if not hasattr(Updater, '_Updater__polling_cleanup_cb'):
        def _patch_init(self, *args, **kwargs):
            self._polling_cleanup_cb = None
        Updater.__init__ = _patch_init

# Configuración
TOKEN = "8960529925:AAGcOZHg8O-oVH_pRJ6CGwLvaRuXpN54lcI"
ID_ADMIN = 5353490913

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ARCHIVO_CONFIG = "config.json"

config_default = {
    "mensaje_bienvenida": "¡Bienvenido al grupo! 🎉\n\nTe damos la bienvenida a nuestra comunidad.\n\n📌 Por favor, lee las reglas y preséntate.",
    "botones": [
        {"texto": "📢 Canal Oficial", "url": "https://t.me/tucanal"},
        {"texto": "📋 Reglas del Grupo", "url": "https://t.me/tusreglas"}
    ]
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

# --- MENÚ PRINCIPAL ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        await update.message.reply_text("❌ No tienes permiso para usar este bot.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📝 Cambiar Bienvenida", callback_data="menu_welcome")],
        [InlineKeyboardButton("🔘 Configurar Botones", callback_data="menu_buttons")],
        [InlineKeyboardButton("👁️ Ver Vista Previa", callback_data="menu_preview")],
        [InlineKeyboardButton("🔄 Resetear Configuración", callback_data="menu_reset")],
        [InlineKeyboardButton("ℹ️ Estado del Bot", callback_data="menu_status")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *Panel de Control - Bot de Bienvenidas*\n\n"
        "Selecciona una opción para configurar tu bot.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# --- MANEJADOR DE BOTONES DEL MENÚ ---

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ID_ADMIN:
        await query.edit_message_text("❌ No tienes permiso.")
        return
    
    data = query.data
    
    if data == "menu_welcome":
        await query.edit_message_text(
            "📝 *Cambiar mensaje de bienvenida*\n\n"
            "Envía el nuevo mensaje.\n"
            "Para cancelar, escribe /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'welcome'
    
    elif data == "menu_buttons":
        config = cargar_config()
        botones = config.get('botones', [])
        
        texto = "🔘 *Configurar Botones*\n\n"
        if botones:
            texto += "Botones actuales:\n"
            for i, btn in enumerate(botones, 1):
                texto += f"{i}. {btn['texto']} → {btn['url']}\n"
        else:
            texto += "No hay botones configurados.\n"
        
        texto += "\nEnvía los botones en este formato:\n"
        texto += "`Texto1|url1, Texto2|url2`\n\n"
        texto += "Ejemplo:\n"
        texto += "`📢 Canal|https://t.me/mi_canal, 💬 Reglas|https://t.me/reglas`"
        
        await query.edit_message_text(texto, parse_mode="Markdown")
        context.user_data['esperando'] = 'buttons'
    
    elif data == "menu_preview":
        config = cargar_config()
        mensaje = config.get('mensaje_bienvenida', config_default['mensaje_bienvenida'])
        botones = config.get('botones', config_default['botones'])
        
        keyboard = [[InlineKeyboardButton(b['texto'], url=b['url'])] for b in botones]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "👁️ *Vista previa:*\n\n" + mensaje,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "menu_reset":
        guardar_config(config_default)
        await query.edit_message_text("✅ Configuración restaurada.")
    
    elif data == "menu_status":
        config = cargar_config()
        botones = config.get('botones', [])
        
        texto = "ℹ️ *Estado del Bot*\n\n"
        texto += f"✅ Bot activo\n"
        texto += f"📝 {len(config.get('mensaje_bienvenida', ''))} caracteres\n"
        texto += f"🔘 {len(botones)} botones\n"
        
        await query.edit_message_text(texto, parse_mode="Markdown")

# --- COMANDOS ---

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    await update.message.reply_text("📝 Envía el nuevo mensaje de bienvenida. Para cancelar, escribe /cancelar")
    context.user_data['esperando'] = 'welcome'

async def set_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    await update.message.reply_text(
        "🔘 Envía los botones en formato:\n"
        "`Texto1|url1, Texto2|url2`"
    )
    context.user_data['esperando'] = 'buttons'

async def preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    config = cargar_config()
    mensaje = config.get('mensaje_bienvenida', config_default['mensaje_bienvenida'])
    botones = config.get('botones', config_default['botones'])
    
    keyboard = [[InlineKeyboardButton(b['texto'], url=b['url'])] for b in botones]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👁️ *Vista previa:*\n\n" + mensaje,
        parse_mode="Markdown",
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
    await update.message.reply_text(
        f"ℹ️ *Estado*\n\n"
        f"✅ Bot activo\n"
        f"📝 {len(config.get('mensaje_bienvenida', ''))} caracteres\n"
        f"🔘 {len(botones)} botones",
        parse_mode="Markdown"
    )

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('esperando', None)
    await update.message.reply_text("✅ Operación cancelada.")

# --- MANEJO DE CONFIGURACIÓN ---

async def handle_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    estado = context.user_data.get('esperando')
    if not estado:
        return
    
    texto = update.message.text
    config = cargar_config()
    
    if estado == 'welcome':
        config['mensaje_bienvenida'] = texto
        guardar_config(config)
        await update.message.reply_text("✅ Mensaje actualizado.")
        context.user_data.pop('esperando', None)
    
    elif estado == 'buttons':
        try:
            nuevos_botones = []
            for item in texto.split(','):
                parte = item.strip().split('|')
                if len(parte) == 2:
                    nuevos_botones.append({
                        "texto": parte[0].strip(),
                        "url": parte[1].strip()
                    })
            if nuevos_botones:
                config['botones'] = nuevos_botones
                guardar_config(config)
                await update.message.reply_text(f"✅ {len(nuevos_botones)} botones configurados.")
            else:
                await update.message.reply_text("❌ Formato incorrecto.")
            context.user_data.pop('esperando', None)
        except:
            await update.message.reply_text("❌ Error. Usa: Texto1|url1, Texto2|url2")

# --- SOLICITUDES DE UNIÓN ---

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        join_request = update.chat_join_request
        user = join_request.from_user
        chat = join_request.chat
        
        logger.info(f"Nueva solicitud de {user.first_name} (@{user.username})")
        
        # Aprobar automáticamente
        await context.bot.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
        
        # Enviar mensaje de bienvenida
        config = cargar_config()
        mensaje = config.get('mensaje_bienvenida', config_default['mensaje_bienvenida'])
        botones = config.get('botones', config_default['botones'])
        
        keyboard = [[InlineKeyboardButton(b['texto'], url=b['url'])] for b in botones]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user.id,
            text=f"👋 ¡Hola {user.first_name}!\n\n" + mensaje,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")

# --- INICIO ---

def main():
    logger.info("🚀 Iniciando bot...")
    
    application = Application.builder().token(TOKEN).build()
    
    # Comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setwelcome", set_welcome))
    application.add_handler(CommandHandler("setbuttons", set_buttons))
    application.add_handler(CommandHandler("preview", preview))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("cancelar", cancelar))
    
    # Callbacks del menú
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="menu_"))
    
    # Configuración
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_config))
    
    # Solicitudes de unión
    application.add_handler(MessageHandler(filters.StatusUpdate.CHAT_JOIN_REQUEST, handle_join_request))
    
    logger.info("✅ Bot iniciado correctamente!")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()