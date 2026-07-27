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

TOKEN = "8501732432:AAHcvGDBfC-c3B0JerQu8tp0A-EQrfBjpNQ"
ID_ADMIN = 5353490913

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ARCHIVO_CONFIG = "config.json"
ARCHIVO_REGISTRO = "registro.json"

config_default = {
    "grupos": {},
    "mensaje_bienvenida": "¡Bienvenido al grupo! 🎉",
    "mensaje_reingreso": "¡Bienvenido de nuevo {NAME}! 🎉",
    "mensaje_despedida": "¡Hasta luego {NAME}! 👋",
    "botones_bienvenida": [],
    "mensajes_programados": [],
    "auto_aprobar": True,
    "tiempo_aprobacion": 0,
    "share_text": "🔞 Únete al mejor grupo +18 😏 🔥 https://kut.lat/eEva"
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

def get_grupo_config(grupo_id):
    config = cargar_config()
    gid = str(grupo_id)
    
    if gid not in config.get('grupos', {}):
        config['grupos'][gid] = {
            "mensaje_bienvenida": config_default['mensaje_bienvenida'],
            "mensaje_reingreso": config_default['mensaje_reingreso'],
            "mensaje_despedida": config_default['mensaje_despedida'],
            "botones_bienvenida": [],
            "auto_aprobar": True,
            "tiempo_aprobacion": 0,
            "mensajes_programados": [],
            "share_text": config_default['share_text']
        }
        guardar_config(config)
    
    return config['grupos'][gid]

def guardar_grupo_config(grupo_id, grupo_config):
    config = cargar_config()
    config['grupos'][str(grupo_id)] = grupo_config
    guardar_config(config)

def obtener_variables(user, chat=None, grupo_config=None):
    return {
        "{NAME}": user.first_name or "",
        "{MENTION}": f'<a href="tg://user?id={user.id}">{user.first_name or "Usuario"}</a>',
        "{USERNAME}": f"@{user.username}" if user.username else "",
        "{GROUPNAME}": chat.title if chat else "",
        "{DATE}": datetime.now().strftime("%d/%m/%Y"),
        "{TIME}": datetime.now().strftime("%H:%M"),
    }

def procesar_mensaje(texto, variables):
    for key, value in variables.items():
        texto = texto.replace(key, str(value))
    return texto

def crear_botones(botones_config, share_text=None):
    if not botones_config and not share_text:
        return None
    
    keyboard = []
    fila = []
    
    if share_text:
        fila.append(InlineKeyboardButton("📤 Compartir", switch_inline_query=share_text))
    
    for b in botones_config:
        if b.get('tipo') == 'url':
            fila.append(InlineKeyboardButton(b['texto'], url=b['url']))
        elif b.get('tipo') == 'alert':
            fila.append(InlineKeyboardButton(b['texto'], callback_data=f"alert_{b.get('alert_text', '¡Mensaje!')}"))
        
        if len(fila) >= 2:
            keyboard.append(fila)
            fila = []
    
    if fila:
        keyboard.append(fila)
    
    return InlineKeyboardMarkup(keyboard) if keyboard else None

def procesar_botones(texto):
    if not texto:
        return []
    
    botones = []
    for linea in texto.strip().split('\n'):
        if ' - ' in linea:
            partes = linea.strip().split(' - ', 1)
            titulo = partes[0].strip()
            accion = partes[1].strip()
            
            if accion.startswith('popup:') or accion.startswith('alert:'):
                botones.append({"tipo": "alert", "texto": titulo, "alert_text": accion.replace('popup:', '').replace('alert:', '')})
            elif accion.startswith('t.me/') or accion.startswith('https://'):
                if not accion.startswith('http'):
                    accion = 'https://' + accion
                botones.append({"tipo": "url", "texto": titulo, "url": accion})
    
    return botones

async def start(update, context):
    if update.effective_user.id != ID_ADMIN:
        await update.message.reply_text("❌ No tienes permiso.")
        return
    
    if update.message.chat.type in ['group', 'supergroup']:
        grupo_id = update.message.chat_id
        get_grupo_config(grupo_id)
        await update.message.reply_text(
            "🤖 *Configuración del grupo*\n\n"
            "La configuración se realiza en el chat privado.\n"
            "📌 Abre el chat privado con el bot y usa /start.",
            parse_mode="Markdown"
        )
        return
    
    config = cargar_config()
    grupos = config.get('grupos', {})
    
    if grupos:
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
        await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.message.reply_text("🤖 *BOT*\n\nNo hay grupos configurados.")

async def menu_principal(update, context, edit=False, grupo_id=None):
    query = update.callback_query if edit else None
    
    if not grupo_id and query:
        grupo_id = query.message.chat_id
    elif not grupo_id and update.message:
        grupo_id = update.message.chat_id
    
    grupo_config = get_grupo_config(grupo_id)
    
    keyboard = [
        [InlineKeyboardButton("📝 Mensaje Bienvenida", callback_data=f"menu_welcome_{grupo_id}")],
        [InlineKeyboardButton("📨 Mensajes Programados", callback_data=f"menu_mensajes_{grupo_id}")],
        [InlineKeyboardButton("✅ Auto-Aprobación", callback_data=f"menu_auto_{grupo_id}")],
        [InlineKeyboardButton("⏰ Tiempo Aprobación", callback_data=f"menu_tiempo_{grupo_id}")],
        [InlineKeyboardButton("📤 Texto Compartir", callback_data=f"menu_share_{grupo_id}")],
        [InlineKeyboardButton("📋 Listar Grupos", callback_data="menu_list_grupos")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    texto = (
        f"🤖 *CONFIGURACIÓN*\n\n"
        f"📌 Grupo: `{grupo_id}`\n"
        f"✅ Auto-Aprobación: {'ON' if grupo_config.get('auto_aprobar', True) else 'OFF'}\n"
        f"⏰ Tiempo: {grupo_config.get('tiempo_aprobacion', 0)}s\n\n"
        f"Selecciona una opción:"
    )
    
    if edit and query:
        await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
        await query.answer()
    else:
        await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=reply_markup)

async def menu_welcome(update, context, grupo_id):
    query = update.callback_query
    grupo_config = get_grupo_config(grupo_id)
    
    keyboard = [
        [InlineKeyboardButton("📝 Editar Texto", callback_data=f"welcome_text_{grupo_id}")],
        [InlineKeyboardButton("🔘 Botones", callback_data=f"welcome_buttons_{grupo_id}")],
        [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📝 *Mensaje de bienvenida*\n\nSelecciona qué configurar:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await query.answer()

async def menu_mensajes(update, context, grupo_id):
    query = update.callback_query
    grupo_config = get_grupo_config(grupo_id)
    mensajes = grupo_config.get('mensajes_programados', [])
    
    texto = f"📨 *Mensajes Programados*\n\n"
    if mensajes:
        for i, msg in enumerate(mensajes, 1):
            seg = msg.get('intervalo', 3600)
            texto += f"{i}. Cada {seg/60:.0f}min: {msg.get('mensaje', '')[:30]}...\n"
    else:
        texto += "No hay mensajes.\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Agregar", callback_data=f"mensaje_add_{grupo_id}")],
        [InlineKeyboardButton("🗑️ Eliminar", callback_data=f"mensaje_del_{grupo_id}")],
        [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
    await query.answer()

async def menu_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ID_ADMIN:
        await query.edit_message_text("❌ No tienes permiso.")
        return
    
    data = query.data
    
    if data.startswith("alert_"):
        await query.answer(data.replace('alert_', ''), show_alert=True)
        return
    
    if data == "menu_list_grupos":
        await listar_grupos(update, context)
        return
    
    if data.startswith("menu_grupo_"):
        grupo_id = data.replace("menu_grupo_", "")
        await menu_principal(update, context, edit=True, grupo_id=int(grupo_id))
        return
    
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
    
    if data.startswith("menu_welcome_"):
        await menu_welcome(update, context, grupo_id)
        return
    
    if data.startswith("menu_mensajes_"):
        await menu_mensajes(update, context, grupo_id)
        return
    
    if data.startswith("welcome_text_"):
        await query.edit_message_text(
            "✏️ *Editar Mensaje*\n\nVariables: `{NAME}`, `{MENTION}`, `{USERNAME}`, `{GROUPNAME}`\n\nPara cancelar: /cancelar",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'welcome_text'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("welcome_buttons_"):
        keyboard = [
            [InlineKeyboardButton("➕ Agregar", callback_data=f"botones_add_{grupo_id}")],
            [InlineKeyboardButton("🗑️ Eliminar Todos", callback_data=f"botones_clear_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_welcome_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        botones = grupo_config.get('botones_bienvenida', [])
        texto = f"🔘 *Botones*\n\n"
        if botones:
            for i, b in enumerate(botones, 1):
                texto += f"{i}. {b['texto']}\n"
        else:
            texto += "No hay botones.\n"
        
        await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=reply_markup)
        return
    
    if data.startswith("botones_add_"):
        await query.edit_message_text(
            "✏️ *Agregar Botones*\n\nFormato: `Título - t.me/enlace`\nPopup: `Título - popup:Texto`\n\nEjemplo: `📢 Canal - t.me/mi_canal`",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'botones_bienvenida'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("botones_clear_"):
        grupo_config['botones_bienvenida'] = []
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text("✅ Botones eliminados")
        await menu_welcome(update, context, grupo_id)
        return
    
    if data.startswith("mensaje_add_"):
        await query.edit_message_text(
            "📝 *Agregar Mensaje*\n\nEnvía: `segundos|mensaje`\nEjemplo: `120|¡Hola {NAME}!`\n\nMínimo 60 segundos",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'addmsg'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("mensaje_del_"):
        await query.edit_message_text(
            "🗑️ *Eliminar Mensaje*\n\nEnvía el número: `1`",
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'delmsg'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("menu_auto_"):
        keyboard = [
            [InlineKeyboardButton("✅ Activar", callback_data=f"auto_on_{grupo_id}")],
            [InlineKeyboardButton("❌ Desactivar", callback_data=f"auto_off_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        estado = "ON" if grupo_config.get('auto_aprobar', True) else "OFF"
        await query.edit_message_text(f"✅ *AUTO-APROBACIÓN*\n\nEstado: {estado}", parse_mode="Markdown", reply_markup=reply_markup)
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
    
    if data.startswith("menu_tiempo_"):
        keyboard = [
            [InlineKeyboardButton("⚡ Inmediata", callback_data=f"t_0_{grupo_id}")],
            [InlineKeyboardButton("⏰ 30s", callback_data=f"t_30_{grupo_id}")],
            [InlineKeyboardButton("⏰ 60s", callback_data=f"t_60_{grupo_id}")],
            [InlineKeyboardButton("⏰ 120s", callback_data=f"t_120_{grupo_id}")],
            [InlineKeyboardButton("🔙 Atrás", callback_data=f"menu_back_{grupo_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        tiempo = grupo_config.get('tiempo_aprobacion', 0)
        await query.edit_message_text(f"⏰ *TIEMPO*\n\nActual: {tiempo}s", parse_mode="Markdown", reply_markup=reply_markup)
        return
    
    if data.startswith("t_"):
        segundos = int(data.split('_')[1])
        grupo_config['tiempo_aprobacion'] = segundos
        guardar_grupo_config(grupo_id, grupo_config)
        await query.edit_message_text(f"✅ {segundos}s")
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return
    
    if data.startswith("menu_share_"):
        await query.edit_message_text(
            "📤 *Texto para Compartir*\n\nEnvía el texto que aparecerá al usar COMPARTIR.\n\nActual:\n`{}`\n\nPara cancelar: /cancelar".format(grupo_config.get('share_text', 'No configurado')),
            parse_mode="Markdown"
        )
        context.user_data['esperando'] = 'share_text'
        context.user_data['grupo_id'] = grupo_id
        return
    
    if data.startswith("menu_back_"):
        await menu_principal(update, context, edit=True, grupo_id=grupo_id)
        return

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

async def cancelar(update, context):
    context.user_data.clear()
    await update.message.reply_text("✅ Cancelado.")

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
    
    if estado == 'welcome_text':
        grupo_config['mensaje_bienvenida'] = update.message.text
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text("✅ Mensaje actualizado.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return
    
    if estado == 'share_text':
        grupo_config['share_text'] = update.message.text
        guardar_grupo_config(grupo_id, grupo_config)
        await update.message.reply_text("✅ Texto compartir actualizado.")
        context.user_data.clear()
        await menu_principal(update, context, grupo_id=grupo_id)
        return
    
    if estado == 'botones_bienvenida':
        botones = procesar_botones(update.message.text)
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
            
            if 'mensajes_programados' not in grupo_config:
                grupo_config['mensajes_programados'] = []
            
            grupo_config['mensajes_programados'].append({
                "intervalo": segundos,
                "mensaje": partes[1]
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
        share_text = grupo_config.get('share_text', config_default['share_text'])
        
        try:
            chat_members = await context.bot.get_chat_administrators(grupo_id)
            user_ids = [m.user.id for m in chat_members]
        except:
            return
        
        if not user_ids:
            return
        
        try:
            chat = await context.bot.get_chat(grupo_id)
        except:
            chat = None
        
        for msg_config in grupo_config.get('mensajes_programados', []):
            mensaje = msg_config.get('mensaje', '')
            
            for user_id in user_ids:
                try:
                    try:
                        user = await context.bot.get_chat(user_id)
                    except:
                        continue
                    
                    variables = obtener_variables(user, chat, grupo_config)
                    texto = procesar_mensaje(mensaje, variables)
                    share_text_procesado = procesar_mensaje(share_text, variables)
                    reply_markup = crear_botones([], share_text_procesado)
                    
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=texto,
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                        protect_content=True
                    )
                    
                    logger.info(f"✅ Mensaje enviado a {user_id}")
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error enviando a {user_id}: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error en enviar_mensaje_programado: {str(e)}")

async def handle_join_request(update, context):
    try:
        if not update.chat_join_request:
            return
            
        join_request = update.chat_join_request
        user = join_request.from_user
        chat = join_request.chat
        grupo_id = chat.id
        
        grupo_config = get_grupo_config(grupo_id)
        share_text = grupo_config.get('share_text', config_default['share_text'])
        
        variables = obtener_variables(user, chat, grupo_config)
        mensaje = grupo_config.get('mensaje_bienvenida', config_default['mensaje_bienvenida'])
        mensaje_personalizado = procesar_mensaje(mensaje, variables)
        share_text_procesado = procesar_mensaje(share_text, variables)
        botones = grupo_config.get('botones_bienvenida', [])
        reply_markup = crear_botones(botones, share_text_procesado)
        
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=f"👋 ¡Hola!\n\n{mensaje_personalizado}",
                parse_mode="HTML",
                reply_markup=reply_markup,
                protect_content=True
            )
            logger.info(f"✅ Bienvenida enviada a {user.first_name}")
        except Exception as e:
            logger.error(f"Error: {str(e)}")
        
        auto_aprobar = grupo_config.get('auto_aprobar', True)
        tiempo_aprobacion = grupo_config.get('tiempo_aprobacion', 0)
        
        if auto_aprobar:
            if tiempo_aprobacion > 0:
                async def aprobar_despues():
                    await asyncio.sleep(tiempo_aprobacion)
                    try:
                        await context.bot.approve_chat_join_request(chat_id=grupo_id, user_id=user.id)
                        logger.info(f"✅ {user.first_name} aprobado")
                    except Exception as e:
                        logger.error(f"Error: {str(e)}")
                asyncio.create_task(aprobar_despues())
            else:
                try:
                    await context.bot.approve_chat_join_request(chat_id=grupo_id, user_id=user.id)
                    logger.info(f"✅ {user.first_name} aprobado inmediatamente")
                except Exception as e:
                    logger.error(f"Error: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error en handle_join_request: {str(e)}")

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
                logger.info(f"✅ Despedida enviada a {user.first_name}")
            except:
                pass
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")

async def borrar_mensajes_usuario(update, context):
    if update.effective_user.id != ID_ADMIN:
        return
    
    if update.message.chat.type != 'private':
        return
    
    try:
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
        logger.info("🗑️ Mensaje de usuario borrado")
    except:
        pass

def main():
    logger.info("🚀 Iniciando Bot...")
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancelar", cancelar))
    
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="menu_|welcome_|botones_|mensaje_|auto_|t_|alert_"))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_config))
    
    application.add_handler(MessageHandler(filters.ALL & filters.ChatType.PRIVATE, borrar_mensajes_usuario))
    
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    application.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    
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
