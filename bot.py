import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, JobQueue

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
    ],
    "media_bienvenida": None,  # {"tipo": "foto" o "video", "file_id": "..."}
    "mensajes_programados": [
        # {"intervalo": 3600, "mensaje": "Hola {nombre}!", "media": None}
    ],
    "grupo_id": None
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

# --- COMANDOS PRINCIPALES ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        await update.message.reply_text("❌ No tienes permiso.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📝 Configurar Bienvenida", callback_data="menu_welcome")],
        [InlineKeyboardButton("🖼️ Configurar Media", callback_data="menu_media")],
        [InlineKeyboardButton("🔘 Configurar Botones", callback_data="menu_buttons")],
        [InlineKeyboardButton("📨 Mensajes Programados", callback_data="menu_mensajes")],
        [InlineKeyboardButton("👁️ Vista Previa", callback_data="menu_preview")],
        [InlineKeyboardButton("🔄 Resetear", callback_data="menu_reset")],
        [InlineKeyboardButton("ℹ️ Estado del Bot", callback_data="menu_status")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *Panel de Control - Bot Avanzado*\n\n"
        "Selecciona una opción para configurar:\n\n"
        "📌 *Funciones disponibles:*\n"
        "• Mensajes de bienvenida con fotos/videos\n"
        "• Botones personalizados (incluye 'Compartir')\n"
        "• Mensajes automáticos programados\n"
        "• Personalización con nombre del usuario",
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
    config = cargar_config()
    
    if data == "menu_welcome":
        await query.edit_message_text(
            "📝 *Configurar mensaje de bienvenida*\n\n"
            "Envía el nuevo mensaje.\n"
            "Puedes usar *negrita*, _cursiva_ y [enlaces](url).\n"
            "Usa {nombre} para mostrar el nombre del usuario.\n\n"
            "Ejemplo:\n"
            "`¡Bienvenido {nombre}! 🎉`\n\n"
            "Para cancelar, escribe /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'welcome'
    
    elif data == "menu_media":
        await query.edit_message_text(
            "🖼️ *Configurar media de bienvenida*\n\n"
            "Envía una **foto** o **video** que quieras usar.\n"
            "El bot lo guardará y lo enviará junto al mensaje.\n\n"
            "Para eliminar la media, usa /removemedia\n"
            "Para cancelar, escribe /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'media'
    
    elif data == "menu_buttons":
        botones = config.get('botones', [])
        
        texto = "🔘 *Configurar botones*\n\n"
        if botones:
            texto += "Botones actuales:\n"
            for i, btn in enumerate(botones, 1):
                if btn['texto'] == "📤 Compartir grupo":
                    texto += f"{i}. 📤 Compartir grupo\n"
                else:
                    texto += f"{i}. {btn['texto']} → {btn['url']}\n"
        else:
            texto += "No hay botones configurados.\n"
        
        texto += "\nEnvía los botones en formato:\n"
        texto += "`Texto1|url1, Texto2|url2`\n\n"
        texto += "📤 Para el botón *Compartir grupo*, usa:\n"
        texto += "`Compartir grupo`\n\n"
        texto += "Ejemplo:\n"
        texto += "`📢 Canal|https://t.me/mi_canal, 📤 Compartir grupo`"
        
        await query.edit_message_text(texto, parse_mode="Markdown")
        context.user_data['esperando'] = 'buttons'
    
    elif data == "menu_mensajes":
        mensajes = config.get('mensajes_programados', [])
        
        texto = "📨 *Mensajes Programados*\n\n"
        if mensajes:
            texto += "Mensajes activos:\n"
            for i, msg in enumerate(mensajes, 1):
                horas = msg.get('intervalo', 3600) / 3600
                texto += f"{i}. Cada {horas}h: {msg.get('mensaje', '')[:30]}...\n"
        else:
            texto += "No hay mensajes programados.\n"
        
        texto += "\nComandos:\n"
        texto += "/addmsg `intervalo_horas|mensaje` - Agregar mensaje\n"
        texto += "/addmedia `intervalo_horas` - Agregar mensaje con foto/video\n"
        texto += "/removemsg `número` - Eliminar mensaje\n"
        texto += "/listmsg - Listar mensajes\n\n"
        texto += "Ejemplo:\n"
        texto += "`/addmsg 2|¡Hola {nombre}, recuerda participar!`"
        
        await query.edit_message_text(texto, parse_mode="Markdown")
    
    elif data == "menu_preview":
        await preview(update, context)
        await query.delete_message()
    
    elif data == "menu_reset":
        guardar_config(config_default)
        await query.edit_message_text("✅ Configuración restaurada.")
    
    elif data == "menu_status":
        botones = config.get('botones', [])
        mensajes = config.get('mensajes_programados', [])
        media = config.get('media_bienvenida')
        
        texto = "ℹ️ *Estado del Bot*\n\n"
        texto += f"✅ Bot activo\n"
        texto += f"📝 Mensaje: {len(config.get('mensaje_bienvenida', ''))} caracteres\n"
        texto += f"🖼️ Media: {'✅' if media else '❌'}\n"
        texto += f"🔘 Botones: {len(botones)}\n"
        texto += f"📨 Mensajes programados: {len(mensajes)}\n"
        texto += f"👤 Admin ID: {ID_ADMIN}\n"
        
        if config.get('grupo_id'):
            texto += f"👥 Grupo ID: {config.get('grupo_id')}\n"
        
        await query.edit_message_text(texto, parse_mode="Markdown")

# --- COMANDOS DE MENSAJES PROGRAMADOS ---

async def add_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    try:
        # Formato: /addmsg 2|mensaje
        args = update.message.text.split(' ', 1)
        if len(args) < 2:
            await update.message.reply_text(
                "❌ Usa: `/addmsg intervalo_horas|mensaje`\n"
                "Ejemplo: `/addmsg 2|¡Hola {nombre}!`",
                parse_mode="Markdown"
            )
            return
        
        partes = args[1].split('|', 1)
        if len(partes) != 2:
            await update.message.reply_text("❌ Formato incorrecto. Usa: `horas|mensaje`")
            return
        
        horas = float(partes[0])
        mensaje = partes[1]
        
        config = cargar_config()
        if 'mensajes_programados' not in config:
            config['mensajes_programados'] = []
        
        config['mensajes_programados'].append({
            "intervalo": horas * 3600,  # Convertir a segundos
            "mensaje": mensaje,
            "media": None
        })
        guardar_config(config)
        
        # Programar el nuevo mensaje
        await programar_mensaje(context.application, config)
        
        await update.message.reply_text(f"✅ Mensaje programado cada {horas} horas")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def add_mensaje_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    try:
        args = update.message.text.split(' ', 1)
        if len(args) < 2:
            await update.message.reply_text(
                "❌ Usa: `/addmedia intervalo_horas`\n"
                "Luego envía la foto o video que quieras usar",
                parse_mode="Markdown"
            )
            return
        
        horas = float(args[1])
        context.user_data['esperando_media'] = horas
        
        await update.message.reply_text(
            f"📤 Envía la **foto** o **video** que quieras usar para el mensaje programado cada {horas} horas"
        )
        
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
            
            # Reprogramar
            await programar_mensaje(context.application, config)
            
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
        horas = msg.get('intervalo', 3600) / 3600
        texto += f"{i}. Cada {horas}h: {msg.get('mensaje', '')[:50]}...\n"
        if msg.get('media'):
            texto += "   🖼️ Con media\n"
    
    await update.message.reply_text(texto, parse_mode="Markdown")

# --- FUNCIONES DE MENSAJES PROGRAMADOS ---

async def enviar_mensaje_programado(context: ContextTypes.DEFAULT_TYPE):
    """Envía mensajes programados a todos los miembros del grupo"""
    try:
        config = cargar_config()
        grupo_id = config.get('grupo_id')
        
        if not grupo_id:
            logger.warning("No hay grupo configurado para mensajes programados")
            return
        
        # Obtener miembros del grupo
        try:
            # Intentar obtener la lista de miembros (puede fallar si es grupo muy grande)
            chat_members = await context.bot.get_chat_administrators(grupo_id)
            # Si no tienes permisos, usa esta alternativa
            user_ids = []
            for member in chat_members:
                user_ids.append(member.user.id)
        except:
            # Si no podemos obtener la lista, no enviamos mensajes a usuarios específicos
            logger.warning("No se pueden obtener miembros del grupo")
            return
        
        # Enviar mensaje a cada usuario
        for msg_config in config.get('mensajes_programados', []):
            mensaje = msg_config.get('mensaje', '')
            media = msg_config.get('media')
            
            for user_id in user_ids:
                try:
                    # Personalizar con el nombre del usuario
                    try:
                        user = await context.bot.get_chat(user_id)
                        nombre = user.first_name
                    except:
                        nombre = "Usuario"
                    
                    texto_personalizado = mensaje.replace('{nombre}', nombre)
                    
                    if media:
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
                    
                    await asyncio.sleep(0.5)  # Evitar rate limiting
                    
                except Exception as e:
                    logger.error(f"Error enviando mensaje a {user_id}: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error en enviar_mensaje_programado: {str(e)}")

async def programar_mensaje(application: Application, config: dict):
    """Programa todos los mensajes automáticos"""
    # Limpiar jobs existentes
    current_jobs = application.job_queue.jobs()
    for job in current_jobs:
        if job.name == "mensaje_programado":
            job.schedule_removal()
    
    # Programar nuevos mensajes
    for msg_config in config.get('mensajes_programados', []):
        intervalo = msg_config.get('intervalo', 3600)
        application.job_queue.run_repeating(
            enviar_mensaje_programado,
            interval=intervalo,
            first=10,  # Esperar 10 segundos para iniciar
            name="mensaje_programado"
        )
        logger.info(f"📨 Mensaje programado cada {intervalo/3600} horas")

# --- COMANDOS DE CONFIGURACIÓN ---

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    await update.message.reply_text(
        "📝 Envía el nuevo mensaje de bienvenida.\n"
        "Usa {nombre} para mostrar el nombre del usuario.\n"
        "Para cancelar, escribe /cancelar"
    )
    context.user_data['esperando'] = 'welcome'

async def set_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    await update.message.reply_text(
        "🔘 Envía los botones en formato:\n"
        "`Texto1|url1, Texto2|url2`\n\n"
        "📤 Para el botón *Compartir grupo*, usa:\n"
        "`Compartir grupo`\n\n"
        "Ejemplo:\n"
        "`📢 Canal|https://t.me/mi_canal, 📤 Compartir grupo`"
    )
    context.user_data['esperando'] = 'buttons'

async def preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    config = cargar_config()
    mensaje = config.get('mensaje_bienvenida', config_default['mensaje_bienvenida'])
    botones = config.get('botones', config_default['botones'])
    media = config.get('media_bienvenida')
    
    # Crear botones
    keyboard = []
    for b in botones:
        if b['texto'] == "📤 Compartir grupo" or b['texto'] == "Compartir grupo":
            # Botón de compartir (solo texto, sin URL)
            keyboard.append([InlineKeyboardButton("📤 Compartir grupo", switch_inline_query="")])
        else:
            keyboard.append([InlineKeyboardButton(b['texto'], url=b['url'])])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Enviar vista previa con o sin media
    if media:
        if media.get('tipo') == 'foto':
            await update.message.reply_photo(
                photo=media.get('file_id'),
                caption=f"👁️ *Vista previa:*\n\n" + mensaje,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        elif media.get('tipo') == 'video':
            await update.message.reply_video(
                video=media.get('file_id'),
                caption=f"👁️ *Vista previa:*\n\n" + mensaje,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
    else:
        await update.message.reply_text(
            f"👁️ *Vista previa:*\n\n" + mensaje,
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

async def remove_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    config = cargar_config()
    config['media_bienvenida'] = None
    guardar_config(config)
    await update.message.reply_text("✅ Media de bienvenida eliminada.")

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

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('esperando', None)
    context.user_data.pop('esperando_media', None)
    await update.message.reply_text("✅ Operación cancelada.")

# --- MANEJO DE CONFIGURACIÓN ---

async def handle_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    estado = context.user_data.get('esperando')
    if not estado:
        return
    
    config = cargar_config()
    texto = update.message.text
    
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
                elif item.strip() == "Compartir grupo" or item.strip() == "📤 Compartir grupo":
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
        # Guardar la media
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            config['media_bienvenida'] = {"tipo": "foto", "file_id": file_id}
            guardar_config(config)
            await update.message.reply_text("✅ Foto guardada para la bienvenida.")
        elif update.message.video:
            file_id = update.message.video.file_id
            config['media_bienvenida'] = {"tipo": "video", "file_id": file_id}
            guardar_config(config)
            await update.message.reply_text("✅ Video guardado para la bienvenida.")
        else:
            await update.message.reply_text("❌ Envía una foto o video.")
        
        context.user_data.pop('esperando', None)

# --- MANEJO DE MEDIA PARA MENSAJES PROGRAMADOS ---

async def handle_media_programada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ID_ADMIN:
        return
    
    horas = context.user_data.get('esperando_media')
    if not horas:
        return
    
    config = cargar_config()
    
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        # Agregar mensaje con media
        if 'mensajes_programados' not in config:
            config['mensajes_programados'] = []
        
        config['mensajes_programados'].append({
            "intervalo": horas * 3600,
            "mensaje": "¡Hola {nombre}! Recuerda visitar el grupo 🎉",
            "media": {"tipo": "foto", "file_id": file_id}
        })
        guardar_config(config)
        await programar_mensaje(context.application, config)
        await update.message.reply_text(f"✅ Mensaje con foto programado cada {horas} horas")
        
    elif update.message.video:
        file_id = update.message.video.file_id
        config['mensajes_programados'].append({
            "intervalo": horas * 3600,
            "mensaje": "¡Hola {nombre}! Recuerda visitar el grupo 🎉",
            "media": {"tipo": "video", "file_id": file_id}
        })
        guardar_config(config)
        await programar_mensaje(context.application, config)
        await update.message.reply_text(f"✅ Mensaje con video programado cada {horas} horas")
    else:
        await update.message.reply_text("❌ Envía una foto o video.")
        return
    
    context.user_data.pop('esperando_media', None)

# --- SOLICITUDES DE UNIÓN ---

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        # Guardar ID del grupo
        config = cargar_config()
        if not config.get('grupo_id'):
            config['grupo_id'] = chat.id
            guardar_config(config)
        
        # Cargar configuración
        mensaje = config.get('mensaje_bienvenida', config_default['mensaje_bienvenida'])
        botones = config.get('botones', config_default['botones'])
        media = config.get('media_bienvenida')
        
        # Personalizar mensaje con el nombre del usuario
        mensaje_personalizado = mensaje.replace('{nombre}', user.first_name)
        
        # Crear botones (incluyendo botón de compartir)
        keyboard = []
        for b in botones:
            if b['texto'] == "📤 Compartir grupo" or b['texto'] == "Compartir grupo":
                # Botón de compartir
                keyboard.append([InlineKeyboardButton("📤 Compartir grupo", switch_inline_query="")])
            else:
                keyboard.append([InlineKeyboardButton(b['texto'], url=b['url'])])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        # Enviar mensaje con o sin media
        if media:
            if media.get('tipo') == 'foto':
                await context.bot.send_photo(
                    chat_id=user.id,
                    photo=media.get('file_id'),
                    caption=f"👋 ¡Hola {user.first_name}!\n\n" + mensaje_personalizado,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
            elif media.get('tipo') == 'video':
                await context.bot.send_video(
                    chat_id=user.id,
                    video=media.get('file_id'),
                    caption=f"👋 ¡Hola {user.first_name}!\n\n" + mensaje_personalizado,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
        else:
            await context.bot.send_message(
                chat_id=user.id,
                text=f"👋 ¡Hola {user.first_name}!\n\n" + mensaje_personalizado,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        
        logger.info(f"✅ Bienvenida enviada a {user.first_name}")
        
    except Exception as e:
        logger.error(f"Error en handle_join_request: {str(e)}")

# --- INICIO ---

def main():
    logger.info("🚀 Iniciando bot avanzado...")
    
    # Crear aplicación con JobQueue
    application = Application.builder().token(TOKEN).build()
    
    # Comandos del admin
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setwelcome", set_welcome))
    application.add_handler(CommandHandler("setbuttons", set_buttons))
    application.add_handler(CommandHandler("preview", preview))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("cancelar", cancelar))
    application.add_handler(CommandHandler("removemedia", remove_media))
    application.add_handler(CommandHandler("setgrupo", set_grupo))
    
    # Comandos de mensajes programados
    application.add_handler(CommandHandler("addmsg", add_mensaje))
    application.add_handler(CommandHandler("addmedia", add_mensaje_media))
    application.add_handler(CommandHandler("removemsg", remove_mensaje))
    application.add_handler(CommandHandler("listmsg", list_mensajes))
    
    # Callbacks del menú
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="menu_"))
    
    # Manejar mensajes de configuración
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_config))
    
    # Manejar media para mensajes programados
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO & ~filters.COMMAND, handle_media_programada))
    
    # Manejar solicitudes de unión
    application.add_handler(MessageHandler(filters.ALL, handle_join_request))
    
    # Programar mensajes automáticos
    config = cargar_config()
    if config.get('mensajes_programados'):
        application.job_queue.run_repeating(
            enviar_mensaje_programado,
            interval=10,  # Ejecutar cada 10 segundos (el job interno maneja los intervalos)
            first=10,
            name="mensaje_programado"
        )
    
    logger.info("✅ Bot avanzado iniciado correctamente!")
    logger.info(f"👤 Admin ID: {ID_ADMIN}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
