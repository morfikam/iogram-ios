#!/usr/bin/env python3
# Iogram для Android: правки исходника DrKLO/Telegram перед сборкой (сборка Standalone — установка не из магазина).
# python3 apply.py <папка исходника>
# Ключи берутся из окружения: IOGRAM_API_ID, IOGRAM_API_HASH.
# На GitHub apk подписывается учебным ключом из исходника, настоящая подпись ставится локально (apksigner)
import os
import re
import shutil
import sys

ROOT = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGE = 'com.iogram.messenger'
APP_NAME = 'Iogram'
STANDALONE = 'TMessagesProj_AppStandalone'
MAIN = 'TMessagesProj/src/main'
JAVA = MAIN + '/java/org/telegram'
ICON_BACKGROUND = '#120f3d'
DENSITIES = ['mdpi', 'hdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi']


def read(path):
    with open(os.path.join(ROOT, path), encoding='utf-8', newline='') as source:
        return source.read()


def write(path, text):
    with open(os.path.join(ROOT, path), 'w', encoding='utf-8', newline='') as target:
        target.write(text)


def replace(path, old, new, count=1):
    text = read(path)
    found = text.count(old)
    if found != count:
        sys.exit(f'{path}: «{old}» встречается {found} раз, ожидалось {count}')
    write(path, text.replace(old, new))


def replace_regex(path, pattern, new):
    text, found = re.subn(pattern, new, read(path), flags=re.M)
    if found != 1:
        sys.exit(f'{path}: «{pattern}» найдено {found} раз, ожидалось 1')
    write(path, text)


def apply_keys():
    api_id = os.environ['IOGRAM_API_ID'].strip()
    api_hash = os.environ['IOGRAM_API_HASH'].strip()
    if not api_id.isdigit() or not re.fullmatch('[0-9a-f]{32}', api_hash):
        sys.exit('Неверный формат IOGRAM_API_ID / IOGRAM_API_HASH')
    build_vars = JAVA + '/messenger/BuildVars.java'
    replace_regex(build_vars, r'public static int APP_ID = \d+;', f'public static int APP_ID = {api_id};')
    replace_regex(build_vars, r'public static String APP_HASH = "[0-9a-f]+";', f'public static String APP_HASH = "{api_hash}";')


# Отдельный пакет: приложение ставится рядом с настоящим Telegram
def apply_package():
    replace_regex('gradle.properties', r'^APP_PACKAGE=.*$', f'APP_PACKAGE={PACKAGE}')
    replace(STANDALONE + '/google-services.json', '"package_name": "org.telegram.messenger.web"', f'"package_name": "{PACKAGE}.web"')
    # Тип системной учётной записи уникален: с настоящим Telegram он конфликтует
    replace(JAVA + '/messenger/ContactsController.java', '"org.telegram.messenger"', f'"{PACKAGE}"', 5)
    replace(MAIN + '/res/xml/auth.xml', 'android:accountType="org.telegram.messenger"', f'android:accountType="{PACKAGE}"')
    replace(MAIN + '/res/xml/sync_contacts.xml', 'android:accountType="org.telegram.messenger"', f'android:accountType="{PACKAGE}"')
    replace(MAIN + '/res/xml/auth_menu.xml', 'android:targetPackage="org.telegram.messenger"', f'android:targetPackage="{PACKAGE}.web"')


def apply_name():
    strings = MAIN + '/res/values/strings.xml'
    replace(strings, '<string name="AppName">Telegram</string>', f'<string name="AppName">{APP_NAME}</string>')
    replace(strings, '<string name="AppNameBeta">Telegram Beta</string>', f'<string name="AppNameBeta">{APP_NAME} Beta</string>')
    replace(strings, '<string name="NotificationHiddenName">Telegram</string>', f'<string name="NotificationHiddenName">{APP_NAME}</string>')


def apply_icon():
    res = STANDALONE + '/src/main/res'
    for density in DENSITIES:
        for name in ('ic_launcher_sa.png', 'iogram_foreground.png'):
            shutil.copyfile(os.path.join(HERE, 'icon', density, name), os.path.join(ROOT, res, f'mipmap-{density}', name))
    write(res + '/mipmap-anydpi-v26/ic_launcher_sa.xml',
          '<?xml version="1.0" encoding="utf-8"?>\n'
          '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
          '    <background android:drawable="@color/iogram_icon_background" />\n'
          '    <foreground android:drawable="@mipmap/iogram_foreground" />\n'
          '</adaptive-icon>\n')
    write(res + '/values/iogram.xml',
          '<?xml version="1.0" encoding="utf-8"?>\n'
          f'<resources><color name="iogram_icon_background">{ICON_BACKGROUND}</color></resources>\n')


# Обновления приходят с серверов Telegram и предложили бы поставить официальное приложение
def apply_no_telegram_updates():
    replace(JAVA + '/messenger/BuildVars.java', 'public static boolean CHECK_UPDATES = true;', 'public static boolean CHECK_UPDATES = false;')
    signature = 'public void checkAppUpdate(boolean force, Browser.Progress progress) {'
    replace(JAVA + '/ui/LaunchActivity.java', signature, signature + ' if (progress != null) progress.end(); if (true) return;')


# На GitHub собираем только 64-битный ARM (почти все телефоны) и ускоряем повторные сборки через ccache
def apply_build_speed():
    replace(STANDALONE + '/build.gradle', 'abiFilters "armeabi-v7a", "arm64-v8a", "x86", "x86_64"', 'abiFilters "arm64-v8a"')
    if os.environ.get('IOGRAM_CCACHE'):
        argument = f"'-DANDROID_PLATFORM=android-23', '-DANDROID_CCACHE={os.environ['IOGRAM_CCACHE']}'"
        for path in ('TMessagesProj/build.gradle', STANDALONE + '/build.gradle'):
            replace(path, "'-DANDROID_PLATFORM=android-23'", argument)


apply_keys()
apply_package()
apply_name()
apply_icon()
apply_no_telegram_updates()
apply_build_speed()
print('Правки Iogram применены')
