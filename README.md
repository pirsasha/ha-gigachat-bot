# GigaChat Bot для Home Assistant

Компонент для интеграции Telegram-бота с поддержкой GigaChat AI в Home Assistant.

## Установка

1. Скопируйте папку `gigachat_bot` в директорию `custom_components` вашего Home Assistant
2. Добавьте следующую конфигурацию в ваш `configuration.yaml`:

```yaml
gigachat_bot:
  bot_token: !secret telegram_bot_api_key
  allowed_chat_ids: !secret telegram_allowed_chat_ids
  client_id: !secret gigachat_client_id
  client_secret: !secret gigachat_client_secret
```

3. Добавьте следующие секреты в ваш `secrets.yaml`:

```yaml
telegram_bot_api_key: "ВАШ_ТОКЕН_БОТА"
telegram_allowed_chat_ids:
  - ID_ЧАТА_1
  - ID_ЧАТА_2
gigachat_client_id: "ВАШ_CLIENT_ID"
gigachat_client_secret: "ВАШ_CLIENT_SECRET"
```

## Использование

После установки и настройки компонента, бот будет доступен в указанных чатах Telegram. Он будет отвечать на сообщения, используя GigaChat AI.

### Доступные сервисы

#### `gigachat_bot.refresh_token`
Обновляет токен доступа GigaChat API.

#### `gigachat_bot.send_message`
Отправляет сообщение в указанный чат через бота.

## Отладка

В случае проблем с SSL-сертификатами, компонент временно отключает проверку SSL для диагностики. В продакшн-окружении рекомендуется настроить корректную работу с сертификатами.

## Поддержка

При возникновении проблем, проверьте логи Home Assistant для получения дополнительной информации об ошибках.
