#!/usr/bin/env python3
# Iogram для iPhone: правки поверх официального исходника Telegram-iOS.
# Запуск: python3 iogram/apply.py <папка исходника Telegram-iOS>
# Ключи API берутся из переменных окружения IOGRAM_API_ID и IOGRAM_API_HASH (на GitHub — из Secrets).
# Скрипт можно запускать повторно: уже сделанные правки он узнаёт и не ломает.
import datetime
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
APP_NAME = 'Iogram'
# Свой идентификатор — Iogram ставится рядом с официальным Telegram, а не вместо него
BUNDLE_ID = 'com.iogram.ios'
OFFICIAL_BUNDLE_ID = 'ph.telegra.Telegraph'

TELEGRAM_CORE = os.path.join('submodules', 'TelegramCore', 'Sources')
TELEGRAM_UI = os.path.join('submodules', 'TelegramUI', 'Sources')

# Вставки в TelegramUI (тот же формат, что CORE_PATCHES)
UI_PATCHES = [
    # Подпись сторонним сертификатом (Feather, ESign, бесплатный Apple ID) обычно не даёт общей папки App Group,
    # и Telegram без неё останавливается на чёрном экране («Error 2»). Тогда данные хранятся в папке самого приложения
    # (расширения — виджеты, «Поделиться», уведомления — их не видят, само приложение работает)
    ('AppDelegate.swift',
     '        let maybeAppGroupUrl = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: appGroupName)\n',
     '        var maybeAppGroupUrl = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: appGroupName)\n'
     '        if maybeAppGroupUrl == nil, let supportUrl = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first {\n'
     '            let fallbackUrl = supportUrl.appendingPathComponent("IogramGroup", isDirectory: true)\n'
     '            let _ = try? FileManager.default.createDirectory(at: fallbackUrl, withIntermediateDirectories: true, attributes: nil)\n'
     '            maybeAppGroupUrl = fallbackUrl\n'
     '            IogramDiag.mark("нет App Group — данные в \\(fallbackUrl.path)")\n'
     '        }\n',
     1),
    # Диагностика запуска (IogramDiag): отметки этапов уходят на сервер IOGRAM
    ('AppDelegate.swift',
     '        CrashReportCollector.shared.start()\n',
     '        CrashReportCollector.shared.start()\n'
     '        IogramDiag.start()\n',
     1),
    ('AppDelegate.swift',
     '        let deviceSpecificEncryptionParameters = BuildConfig.deviceSpecificEncryptionParameters(',
     '        IogramDiag.mark("ключи шифрования базы…")\n'
     '        let deviceSpecificEncryptionParameters = BuildConfig.deviceSpecificEncryptionParameters(',
     1),
    ('AppDelegate.swift',
     '        TempBox.initializeShared(',
     '        IogramDiag.mark("ключи шифрования готовы")\n'
     '        TempBox.initializeShared(',
     1),
    ('AppDelegate.swift',
     '        if !writeAbilityTestSuccess {\n',
     '        IogramDiag.mark("проверка записи: \\(writeAbilityTestSuccess)")\n'
     '        if !writeAbilityTestSuccess {\n',
     1),
    ('AppDelegate.swift',
     '        let accountManager: AccountManager<TelegramAccountManagerTypes> = setupAccountManager(',
     '        IogramDiag.mark("база аккаунтов…")\n'
     '        let accountManager: AccountManager<TelegramAccountManagerTypes> = setupAccountManager(',
     1),
    ('AppDelegate.swift',
     '            let sharedContext = SharedAccountContextImpl(',
     '            IogramDiag.mark("создаю основной контекст")\n'
     '            let sharedContext = SharedAccountContextImpl(',
     1),
    ('AppDelegate.swift',
     '        self.sharedContextPromise.set(sharedContextSignal',
     '        IogramDiag.mark("didFinishLaunching дошёл до конца")\n'
     '        self.sharedContextPromise.set(sharedContextSignal',
     1),
]

APP_SOURCES = os.path.join('Telegram', 'Telegram-iOS')

# Диагностика: самая первая строка программы (до UIApplicationMain) — отметка уходит, даже если дальше всё зависнет.
# Ждёт отправку до 3 с, чтобы отметка успела уйти до возможного падения
MAIN_PATCHES = [
    ('main.m',
     '#import <UIKit/UIKit.h>\n',
     '#import <UIKit/UIKit.h>\n'
     '#import <Security/Security.h>\n'
     '\n'
     'static void IogramMainPing(void) {\n'
     '    NSDictionary *info = [[NSBundle mainBundle] infoDictionary];\n'
     '    NSString *bundleId = [[NSBundle mainBundle] bundleIdentifier] ?: @"?";\n'
     '    NSURL *groupUrl = [[NSFileManager defaultManager] containerURLForSecurityApplicationGroupIdentifier:[@"group." stringByAppendingString:bundleId]];\n'
     '    NSDictionary *query = @{ (__bridge id)kSecClass: (__bridge id)kSecClassGenericPassword, (__bridge id)kSecAttrAccount: @"iogramMainProbe", (__bridge id)kSecAttrService: @"", (__bridge id)kSecReturnAttributes: @YES };\n'
     '    CFTypeRef found = NULL;\n'
     '    OSStatus status = SecItemCopyMatching((__bridge CFDictionaryRef)query, &found);\n'
     '    if (status == errSecItemNotFound) {\n'
     '        status = SecItemAdd((__bridge CFDictionaryRef)query, &found);\n'
     '    }\n'
     '    NSString *accessGroup = @"-";\n'
     '    if (status == errSecSuccess && found != NULL) {\n'
     '        accessGroup = [(__bridge NSDictionary *)found objectForKey:(__bridge id)kSecAttrAccessGroup] ?: @"-";\n'
     '    }\n'
     '    if (found != NULL) {\n'
     '        CFRelease(found);\n'
     '    }\n'
     '    NSString *line = [NSString stringWithFormat:@"main: процесс запущен, %@ %@ (%@); общая папка: %@; связка ключей: %d, группа %@", bundleId, info[@"CFBundleShortVersionString"], info[@"CFBundleVersion"], groupUrl != nil ? @"есть" : @"НЕТ", (int)status, accessGroup];\n'
     '    NSDictionary *body = @{ @"device": @"main", @"lines": @[ line ] };\n'
     '    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:[NSURL URLWithString:@"https://iogram.iogram-server.workers.dev/diag"]];\n'
     '    request.HTTPMethod = @"POST";\n'
     '    [request setValue:@"application/json" forHTTPHeaderField:@"Content-Type"];\n'
     '    request.HTTPBody = [NSJSONSerialization dataWithJSONObject:body options:0 error:nil];\n'
     '    request.timeoutInterval = 3.0;\n'
     '    dispatch_semaphore_t done = dispatch_semaphore_create(0);\n'
     '    [[[NSURLSession sharedSession] dataTaskWithRequest:request completionHandler:^(NSData *data, NSURLResponse *response, NSError *error) {\n'
     '        dispatch_semaphore_signal(done);\n'
     '    }] resume];\n'
     '    dispatch_semaphore_wait(done, dispatch_time(DISPATCH_TIME_NOW, (int64_t)(3 * NSEC_PER_SEC)));\n'
     '}\n',
     1),
    ('main.m',
     '    @autoreleasepool {\n        return UIApplicationMain(',
     '    @autoreleasepool {\n        IogramMainPing();\n        return UIApplicationMain(',
     1),
]

PASSCODE_CORE = os.path.join('submodules', 'PasscodeCore', 'Sources')

# Без App Group нельзя и обращаться к связке ключей по группе group.<bundle id>: запрос падает,
# Telegram повторяет его бесконечно — чёрный экран. Тогда ключи хранятся в своей связке приложения
PASSCODE_PATCHES = [
    ('Passcode.swift',
     '        query[kSecAttrAccessGroup as String] = try account.hasPrefix("biometric.") ? self.environment.privateAccessGroup() : self.environment.sharedAccessGroup()\n',
     '        let accessGroup = try account.hasPrefix("biometric.") ? self.environment.privateAccessGroup() : self.environment.sharedAccessGroup()\n'
     '        if !(accessGroup.hasPrefix("group.") && FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: accessGroup) == nil) {\n'
     '            query[kSecAttrAccessGroup as String] = accessGroup\n'
     '        }\n',
     1),
    # Диагностика: подготовка и проверка паскода базы аккаунтов (если они падают, запуск повторяет их бесконечно)
    ('AccountManagerIntegration.swift',
     '                let _ = try PasscodeEnvironment.shared.sharedAccessGroup()\n',
     '                IogramDiag.mark("паскод: подготовка")\n'
     '                let _ = try PasscodeEnvironment.shared.sharedAccessGroup()\n',
     1),
    ('AccountManagerIntegration.swift',
     '                return try resolveAccessChallenge(current, allowMigration: allowMigration)\n',
     '                do {\n'
     '                    let result = try resolveAccessChallenge(current, allowMigration: allowMigration)\n'
     '                    IogramDiag.mark("паскод: проверка прошла")\n'
     '                    return result\n'
     '                } catch {\n'
     '                    IogramDiag.mark("паскод: ОШИБКА \\(error)")\n'
     '                    throw error\n'
     '                }\n',
     1),
]

# Вставки в TelegramCore: (файл, что найти, на что заменить, сколько раз должно найтись).
# Ищется по точному тексту исходника выбранной версии; если Telegram изменил код — сборка остановится с понятной ошибкой
CORE_PATCHES = [
    # Режим призрака: «прочитано» не уходит на сервер (у себя чат прочитан — Telegram держит локальную отметку,
    # пока она впереди серверной)
    ('State/SynchronizePeerReadState.swift',
     '                    return pushSignal\n',
     '                    if IogramSettings.ghostRead {\n'
     '                        pushSignal = .complete()\n'
     '                    }\n'
     '                    return pushSignal\n',
     2),
    # «Печатает…» и прочие действия
    ('State/ManagedLocalInputActivities.swift',
     '                return network.request(Api.functions.messages.setTyping(',
     '                if IogramSettings.ghostTyping {\n'
     '                    return .complete()\n'
     '                }\n'
     '                return network.request(Api.functions.messages.setTyping(',
     1),
    ('State/TypingDraftStop.swift',
     '        return network.request(Api.functions.messages.setTyping(',
     '        if IogramSettings.ghostTyping {\n'
     '            return .complete()\n'
     '        }\n'
     '        return network.request(Api.functions.messages.setTyping(',
     1),
    # «В сети»: серверу всегда «не в сети»
    ('State/ManagedAccountPresence.swift',
     'Api.functions.account.updateStatus(offline: .boolFalse)',
     'Api.functions.account.updateStatus(offline: IogramSettings.ghostOnline ? .boolTrue : .boolFalse)',
     1),
    # Истории: ни «просмотрено», ни счётчик просмотров
    ('State/ManagedSynchronizeViewStoriesOperations.swift',
     '    return network.request(Api.functions.stories.readStories(',
     '    if IogramSettings.ghostStories {\n'
     '        return .complete()\n'
     '    }\n'
     '    return network.request(Api.functions.stories.readStories(',
     1),
    ('TelegramEngine/Messages/Stories.swift',
     '            return account.network.request(Api.functions.stories.incrementStoryViews(',
     '            if IogramSettings.ghostStories {\n'
     '                return .complete()\n'
     '            }\n'
     '            return account.network.request(Api.functions.stories.incrementStoryViews(',
     1),
    # Сохранение удалённых: удаление, пришедшее с сервера, не применяется (свои удаления делаются на телефоне сразу)
    ('State/Sync/StateReplay.swift',
     '                    self.applyDeleteMessagesWithGlobalIds(ids)\n',
     '                    if !IogramSettings.keepDeleted {\n'
     '                        self.applyDeleteMessagesWithGlobalIds(ids)\n'
     '                    }\n',
     1),
    ('State/Sync/StateReplay.swift',
     '                    self.applyDeleteMessages(ids)\n',
     '                    if !IogramSettings.keepDeleted {\n'
     '                        self.applyDeleteMessages(ids)\n'
     '                    }\n',
     1),
]

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
    # (их идентификаторы меняются на BUNDLE_ID в refresh_fake_profiles)
    config = json.loads(read(os.path.join(source, 'build-system', 'appstore-configuration.json')))
    config.update({
        'bundle_id': BUNDLE_ID,
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


def replace_bundle_id(value):
    # Во всех строках профиля: ph.telegra.Telegraph → com.iogram.ios (идентификатор, группы, iCloud и т. д.)
    if isinstance(value, str):
        return value.replace(OFFICIAL_BUNDLE_ID, BUNDLE_ID)
    if isinstance(value, list):
        return [replace_bundle_id(item) for item in value]
    if isinstance(value, dict):
        return {key: replace_bundle_id(item) for key, item in value.items()}
    return value


def patch_core(source):
    core = os.path.join(source, TELEGRAM_CORE)
    target_dir = os.path.join(core, 'Iogram')
    os.makedirs(target_dir, exist_ok=True)
    for name in ('IogramSettings.swift', 'IogramDiag.swift'):
        shutil.copyfile(os.path.join(HERE, 'swift', name), os.path.join(target_dir, name))
    apply_patches(core, CORE_PATCHES)
    print('Iogram: функции в TelegramCore ({} вставок)'.format(len(CORE_PATCHES)))
    apply_patches(os.path.join(source, TELEGRAM_UI), UI_PATCHES)
    print('Iogram: правки TelegramUI ({} вставок)'.format(len(UI_PATCHES)))
    apply_patches(os.path.join(source, PASSCODE_CORE), PASSCODE_PATCHES)
    print('Iogram: правки PasscodeCore ({} вставок)'.format(len(PASSCODE_PATCHES)))
    apply_patches(os.path.join(source, APP_SOURCES), MAIN_PATCHES)
    print('Iogram: отметка в main.m')


def apply_patches(base, patches):
    for relative, old, new, expected in patches:
        path = os.path.join(base, relative)
        text = read(path).replace('\r\n', '\n')
        if new in text:
            continue
        found = text.count(old)
        if found != expected:
            fail('{}: ожидалось {} совпад., найдено {} — исходник Telegram изменился'.format(relative, expected, found))
        write(path, text.replace(old, new))


def refresh_fake_profiles(source):
    # У фейковых профилей подписи в исходнике бывает истёкший срок — тогда Bazel отказывается собирать.
    # Профиль — подписанный CMS plist: достаём plist (`security cms -D`), продлеваем даты и подписываем заново
    # одноразовым сертификатом (подпись самого профиля никто не проверяет; приложение подписывает Sideloadly)
    profiles_dir = os.path.join(source, 'build-system', 'fake-codesigning', 'profiles')
    if not shutil.which('security'):
        print('Iogram: не macOS — профили не продлеваются')
        return
    work = tempfile.mkdtemp()
    key = os.path.join(work, 'key.pem')
    cert = os.path.join(work, 'cert.pem')
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-subj', '/CN=Iogram Fake Profiles',
                    '-days', '3650', '-keyout', key, '-out', cert], check=True, capture_output=True)
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)
    count = 0
    for name in sorted(os.listdir(profiles_dir)):
        if not name.endswith('.mobileprovision'):
            continue
        path = os.path.join(profiles_dir, name)
        decoded = subprocess.run(['security', 'cms', '-D', '-i', path], check=True, capture_output=True).stdout
        profile = replace_bundle_id(plistlib.loads(decoded))
        profile['CreationDate'] = now - datetime.timedelta(days=1)
        profile['ExpirationDate'] = now + datetime.timedelta(days=365)
        plist_path = os.path.join(work, name + '.plist')
        with open(plist_path, 'wb') as f:
            plistlib.dump(profile, f)
        subprocess.run(['openssl', 'cms', '-sign', '-binary', '-nodetach', '-outform', 'DER', '-in', plist_path,
                        '-signer', cert, '-inkey', key, '-out', path], check=True, capture_output=True)
        check = plistlib.loads(subprocess.run(['security', 'cms', '-D', '-i', path], check=True,
                                              capture_output=True).stdout)
        if check['ExpirationDate'] != profile['ExpirationDate']:
            fail('профиль {} не продлился'.format(name))
        count += 1
    print('Iogram: фейковые профили продлены до {} ({} шт.)'.format(
        (now + datetime.timedelta(days=365)).date(), count))


def main():
    if len(sys.argv) != 2:
        fail('укажите папку исходника Telegram-iOS')
    source = sys.argv[1]
    if not os.path.exists(os.path.join(source, 'versions.json')):
        fail('в {} нет исходника Telegram-iOS'.format(source))
    write_configuration(source)
    patch_app_name(source)
    patch_icon(source)
    patch_core(source)
    refresh_fake_profiles(source)


if __name__ == '__main__':
    main()
