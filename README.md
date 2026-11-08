# Iogram для iPhone

Неофициальный клиент Telegram на основе официального исходника
[Telegram-iOS](https://github.com/TelegramMessenger/Telegram-iOS) (GPL-2.0).
Это не приложение Telegram и не связано с Telegram FZ-LLC.

Здесь лежат только правки Iogram (`iogram/`) и сценарий сборки (`.github/workflows/build.yml`):
GitHub сам скачивает исходник Telegram-iOS нужной версии, применяет правки и собирает `.ipa` на своём Mac.

## Сборка

1. В настройках репозитория → Secrets and variables → Actions задать `IOGRAM_API_ID` и `IOGRAM_API_HASH`
   (ключи с [my.telegram.org/apps](https://my.telegram.org/apps)) и `IOGRAM_ARTIFACT_KEY` — длинный случайный пароль.
2. Actions → **Build Iogram IPA** → Run workflow (или любой push в `main`). Сборка идёт 1–3 часа.
3. Скачать артефакт **Iogram-ipa** из запуска — внутри `Iogram.ipa.enc`, зашифрованный этим паролем
   (в приложении ваши ключи API, а артефакты открытого репозитория доступны всем).
   Расшифровать: `node iogram/decrypt.mjs Iogram.ipa.enc Iogram.ipa <файл с паролем>`.

## Установка на iPhone

Через [Sideloadly](https://sideloadly.io) (Windows/Mac): подключить iPhone кабелем, перетащить `Iogram.ipa`,
ввести свой Apple ID, нажать Start. На iPhone: Настройки → Основные → VPN и управление устройством → доверять.
С бесплатным Apple ID приложение нужно переподписывать раз в 7 дней (снова Start в Sideloadly, данные сохраняются).

## Что уже сделано

- Название «Iogram», свой значок, свои ключи API.

## План

- Режим призрака (не отправлять «прочитано», «печатает», онлайн).
- Сохранение удалённых сообщений и истории правок.
- Снятие запрета на копирование, скрытие рекламы, ID и дата регистрации в профиле.
- Кошелёк IOGRAM и подарки (сервер iogram.iogram-server.workers.dev).
