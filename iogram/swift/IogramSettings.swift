import Foundation

// Iogram: настройки функций в духе AyuGram. Хранятся в UserDefaults приложения, по умолчанию всё включено.
// Читаются из разных потоков TelegramCore (UserDefaults потокобезопасен), меняются в Настройки → Iogram.
public enum IogramSettings {
    public static let ghostReadKey = "iogram.ghost.read"
    public static let ghostTypingKey = "iogram.ghost.typing"
    public static let ghostOnlineKey = "iogram.ghost.online"
    public static let ghostStoriesKey = "iogram.ghost.stories"
    public static let keepDeletedKey = "iogram.keepDeleted"

    // Не отправлять «прочитано»: собеседник видит одну галочку, у себя сообщения прочитаны
    public static var ghostRead: Bool {
        get { return flag(ghostReadKey) }
        set { UserDefaults.standard.set(newValue, forKey: ghostReadKey) }
    }

    // Не отправлять «печатает…», «записывает голосовое» и т. п.
    public static var ghostTyping: Bool {
        get { return flag(ghostTypingKey) }
        set { UserDefaults.standard.set(newValue, forKey: ghostTypingKey) }
    }

    // Не показывать «в сети»: серверу всегда сообщается «не в сети»
    public static var ghostOnline: Bool {
        get { return flag(ghostOnlineKey) }
        set { UserDefaults.standard.set(newValue, forKey: ghostOnlineKey) }
    }

    // Смотреть истории незаметно: просмотр не уходит автору
    public static var ghostStories: Bool {
        get { return flag(ghostStoriesKey) }
        set { UserDefaults.standard.set(newValue, forKey: ghostStoriesKey) }
    }

    // Не стирать сообщения, которые удалил собеседник или администратор
    public static var keepDeleted: Bool {
        get { return flag(keepDeletedKey) }
        set { UserDefaults.standard.set(newValue, forKey: keepDeletedKey) }
    }

    private static func flag(_ key: String) -> Bool {
        return UserDefaults.standard.object(forKey: key) as? Bool ?? true
    }
}
