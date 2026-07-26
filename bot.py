import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Configuración
TOKEN = "8960529925:AAGcOZHg8O-oVH_pRJ6CGwLvaRuXpN54lcI"
ID_ADMIN = 5353490913

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ARCHIVO_CONFIG = "config.json"

config_default = {
    "mensaje_bienvenida": "¡Bienvenido al grupo! 🎉\n\nTe damos la bienvenida a nuestra comunidad.",
    "botones": [
        {"texto": "📢 Canal Oficial", "url": "https://t.me/tucanal"},
        {"texto": "📋 Reglas", "url": "https://t.me/tusreglas"}
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

# --- COMANDOS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        await update.message.reply_text("❌ No tienes permiso.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📝 Cambiar Bienvenida", callback_data="menu_welcome")],
        [InlineKeyboardButton("🔘 Configurar Botones", callback_data="menu_buttons")],
        [InlineKeyboardButton("👁️ Vista Previa", callback_data="menu_preview")],
        [InlineKeyboardButton("🔄 Resetear", callback_data="menu_reset")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *Panel de Control*\n\nSelecciona una opción:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ID_ADMIN:
        await query.edit_message_text("❌ No tienes permiso.")
        return
    
    data = query.data
    
    if data == "menu_welcome":
        await query.edit_message_text(
            "📝 Envía el nuevo mensaje de bienvenida.\nPara cancelar, escribe /cancelar"
        )
        context.user_data['esperando'] = 'welcome'
    
    elif data == "menu_buttons":
        config = cargar_config()
        botones = config.get('botones', [])
        
        texto = "🔘 *Botones actuales:*\n\n"
        for i, btn in enumerate(botones, 1):
            texto += f"{i}. {btn['texto']} → {btn['url']}\n"
        
        texto += "\nEnvía los botones en formato:\n"
        texto += "`Texto1|url1, Texto2|url2`"
        
        await query.edit_message_text(texto, parse_mode="Markdown")
        context.user_data['esperando'] = 'buttons'
    
    elif data == "menu_preview":
        config = cargar_config()
        mensaje = config.get('mensaje_bienvenida')
        botones = config.get('botones', [])
        
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

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    await update.message.reply_text("📝 Envía el nuevo mensaje de bienvenida:")
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
    mensaje = config.get('mensaje_bienvenida')
    botones = config.get('botones', [])
    
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

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('esperando', None)
    await update.message.reply_text("✅ Cancelado.")

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

async def handle_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Verificar si es una solicitud de unión
        if not update.chat_join_request:
            return
            
        join_request = update.chat_join_request
        user = join_request.from_user
        chat = join_request.chat
        
        logger.info(f"Nueva solicitud de {user.first_name} (@{user.username})")
        
        # Aprobar automáticamente la solicitud
        await context.bot.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
        logger.info(f"✅ Solicitud aprobada para {user.first_name}")
        
        # Cargar configuración
        config = cargar_config()
        mensaje = config.get('mensaje_bienvenida', config_default['mensaje_bienvenida'])
        botones = config.get('botones', config_default['botones'])
        
        # Crear botones
        keyboard = [[InlineKeyboardButton(b['texto'], url=b['url'])] for b in botones]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Enviar mensaje de bienvenida al usuario (en privado)
        await context.bot.send_message(
            chat_id=user.id,
            text=f"👋 ¡Hola {user.first_name}!\n\n" + mensaje,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
        logger.info(f"✅ Bienvenida enviada a {user.first_name}")
        
    except Exception as e:
        logger.error(f"Error en handle_chat_member_update: {str(e)}")

# --- INICIO ---

def main():
    logger.info("🚀 Iniciando bot...")
    application = Application.builder().token(TOKEN).build()
    
    # Comandos para el admin
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setwelcome", set_welcome))
    application.add_handler(CommandHandler("setbuttons", set_buttons))
    application.add_handler(CommandHandler("preview", preview))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("cancelar", cancelar))
    
    # Callbacks del menú
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="menu_"))
    
    # Manejar mensajes de configuración
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_config))
    
    # Manejar solicitudes de unión
    application.add_handler(MessageHandler(filters.ALL, handle_chat_member_update))
    
    logger.info("✅ Bot iniciado correctamente!")
    logger.info(f"👤 Admin ID: {ID_ADMIN}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
