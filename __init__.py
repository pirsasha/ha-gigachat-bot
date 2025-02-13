"""The GigaChat Bot integration."""
import logging
import voluptuous as vol
import aiohttp
import base64
import uuid
from homeassistant.core import HomeAssistant
from homeassistant.const import EVENT_HOMEASSISTANT_START
import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from .const import (
    DOMAIN,
    CONF_TELEGRAM_BOT_TOKEN,
    CONF_ALLOWED_CHAT_IDS,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    DEFAULT_REQUEST_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_TELEGRAM_BOT_TOKEN): cv.string,
                vol.Required(CONF_ALLOWED_CHAT_IDS): vol.All(cv.ensure_list, [vol.Coerce(int)]),
                vol.Required(CONF_CLIENT_ID): cv.string,
                vol.Required(CONF_CLIENT_SECRET): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the GigaChat Bot component."""
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    hass.data[DOMAIN] = {"config": conf}

    async def refresh_token():
        """Refresh GigaChat access token."""
        try:
            auth_key = base64.b64encode(
                f"{conf[CONF_CLIENT_ID]}:{conf[CONF_CLIENT_SECRET]}".encode()
            ).decode()

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                    headers={
                        "Authorization": f"Basic {auth_key}",
                        "RqUID": str(uuid.uuid4()),
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={"scope": "GIGACHAT_API_PERS"},
                    ssl=False,
                    timeout=DEFAULT_REQUEST_TIMEOUT,
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        token = result["access_token"]
                        hass.states.async_set("gigachat_bot.access_token", token)
                        return token
                    _LOGGER.error("Failed to refresh token: %s", await response.text())
                    return None
        except Exception as e:
            _LOGGER.error("Error refreshing token: %s", str(e))
            return None

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming messages."""
        if update.effective_chat.id not in conf[CONF_ALLOWED_CHAT_IDS]:
            _LOGGER.warning(
                "Unauthorized message from chat_id: %s", update.effective_chat.id
            )
            return

        token = hass.states.get("gigachat_bot.access_token")
        if not token:
            token = await refresh_token()
            if not token:
                await update.message.reply_text(
                    "Ошибка авторизации в GigaChat API. Попробуйте позже."
                )
                return

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "GigaChat",
                        "messages": [{"role": "user", "content": update.message.text}],
                        "temperature": 0.7,
                    },
                    ssl=False,
                    timeout=DEFAULT_REQUEST_TIMEOUT,
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        bot_response = result["choices"][0]["message"]["content"]
                        await update.message.reply_text(bot_response)
                    elif response.status == 401:
                        new_token = await refresh_token()
                        if new_token:
                            return await handle_message(update, context)
                        await update.message.reply_text(
                            "Ошибка обновления токена. Попробуйте позже."
                        )
                    else:
                        _LOGGER.error("API error: %s", await response.text())
                        await update.message.reply_text(
                            "Произошла ошибка при обработке запроса."
                        )
        except Exception as e:
            _LOGGER.error("Error: %s", str(e))
            await update.message.reply_text(
                "Произошла ошибка при обработке сообщения."
            )

    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if update.effective_chat.id not in conf[CONF_ALLOWED_CHAT_IDS]:
            return
        await update.message.reply_text(
            "Привет! Я бот с интеграцией GigaChat. Отправьте мне сообщение, и я постараюсь помочь."
        )

    async def start_bot(event):
        """Start the bot when Home Assistant starts."""
        try:
            application = Application.builder().token(conf[CONF_TELEGRAM_BOT_TOKEN]).build()
            application.add_handler(CommandHandler("start", start_command))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            await application.initialize()
            await application.start()
            _LOGGER.info("GigaChat Bot started successfully")
            hass.data[DOMAIN]["application"] = application
            await refresh_token()
        except Exception as e:
            _LOGGER.error("Failed to start bot: %s", str(e))
            return False

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, start_bot)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if "application" in hass.data[DOMAIN]:
        await hass.data[DOMAIN]["application"].stop()
    return True