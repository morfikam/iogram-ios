#!/usr/bin/env python3
# Iogram для iPhone: правки поверх официального исходника Telegram-iOS.
# Запуск: python3 iogram/apply.py <папка исходника Telegram-iOS>
# Ключи API берутся из переменных окружения IOGRAM_API_ID и IOGRAM_API_HASH (на GitHub — из Secrets).
# Скрипт можно запускать повторно: уже сделанные правки он узнаёт и не ломает.
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP_NAME = 'Iogram'

# Фон значка — фиолетовое небо логотипа Iogram (#4A36B8 → #28207A), в тёмной теме — #6C4CE0
ICON_COLOR_REPLACEMENTS = {
    'display-p3:0.21569,0.68627,0.89020,1.00000': 'srgb:0.29020,0.21176,0.72157,1.00000',
    'srgb:0.11373,0.57647,0.82353,1.00000': 'srgb:0.15686,0.12549,0.47843,1.00000',
    'srgb:0.00000,0.47843,1.00000,1.00000': 'srgb:0.42353,0.29804,0.87843,1.00000',
}


def fail(message):
    print('Iogram: ОШИБКА — ' + message)
    sys.exit(1)


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def write(path, text):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def write_configuration(source):
    api_id = os.environ.get('IOGRAM_API_ID', '').strip()
    api_hash = os.environ.get('IOGRAM_API_HASH', '').strip()
    if not api_id.isdigit() or len(api_hash) != 32:
        fail('нет ключей API: задайте Secrets IOGRAM_API_ID и IOGRAM_API_HASH в настройках репозитория')

    # За основу — конфигурация App Store: под неё в исходнике есть фейковые профили подписи
    # (bundle id остаётся прежним — Sideloadly при установке всё равно подписывает своим)
    config = json.loads(read(os.path.join(source, 'build-system', 'appstore-configuration.json')))
    config.update({
        'api_id': api_id,
        'api_hash': api_hash,
        'is_appstore_build': 'false',
        'appstore_id': '0',
        'premium_iap_product_id': '',
        # Siri и iCloud требуют платного аккаунта разработчика Apple
        'enable_siri': False,
        'enable_icloud': False,
    })
    path = os.path.join(source, 'build-system', 'iogram-configuration.json')
    write(path, json.dumps(config, indent=2))
    print('Iogram: конфигурация сборки — ' + path)


def patch_app_name(source):
    path = os.path.join(source, 'Telegram', 'BUILD')
    text = read(path)
    pattern = re.compile(r'(<key>CFBundleDisplayName</key>\s*<string>)Telegram(</string>)')
    text, count = pattern.subn(r'\g<1>' + APP_NAME + r'\g<2>', text)
    if not count and ('<string>' + APP_NAME + '</string>') not in text:
        fail('не нашлось название приложения в Telegram/BUILD — исходник изменился')
    write(path, text)
    print('Iogram: название «{}» ({} мест)'.format(APP_NAME, count))


def patch_icon(source):
    icon_dir = os.path.join(source, 'Telegram', 'Telegram-iOS', 'Telegram.icon')
    glyph = os.path.join(icon_dir, 'Assets', 'Plane.svg')
    if not os.path.exists(glyph):
        fail('не нашлась иконка Telegram.icon — исходник изменился')
    # Слой «самолётик» заменяется луной Io с орбитой (имя файла остаётся, на него ссылается icon.json)
    shutil.copyfile(os.path.join(HERE, 'icon', 'Glyph.svg'), glyph)

    icon_json = os.path.join(icon_dir, 'icon.json')
    text = read(icon_json)
    for old, new in ICON_COLOR_REPLACEMENTS.items():
        text = text.replace(old, new)
    write(icon_json, text)
    print('Iogram: значок заменён')


def main():
    if len(sys.argv) != 2:
        fail('укажите папку исходника Telegram-iOS')
    source = sys.argv[1]
    if not os.path.exists(os.path.join(source, 'versions.json')):
        fail('в {} нет исходника Telegram-iOS'.format(source))
    write_configuration(source)
    patch_app_name(source)
    patch_icon(source)


if __name__ == '__main__':
    main()
