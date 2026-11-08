import Foundation

// Iogram: диагностика запуска на телефоне пользователя (временно, пока сборка с подписью GBox не запускается).
// Отметки этапов, ошибки, падения прошлого запуска и зависания главного потока уходят на сервер IOGRAM (POST /diag).
// Отправка идёт из фонового потока, поэтому работает, даже если главный поток завис.
public final class IogramDiag {
    private static let endpoint = URL(string: "https://iogram.iogram-server.workers.dev/diag")!
    private static let lock = NSLock()
    nonisolated(unsafe) private static var isStarted = false
    nonisolated(unsafe) private static var pending: [String] = []
    nonisolated(unsafe) private static var isSending = false
    nonisolated(unsafe) private static var lastMark = ""
    nonisolated(unsafe) private static var mainPingAt = Date()
    private static let device = String(UUID().uuidString.prefix(8))
    private static let startedAt = Date()

    private static var crashFilePath: String {
        let caches = NSSearchPathForDirectoriesInDomains(.cachesDirectory, .userDomainMask, true).first ?? NSTemporaryDirectory()
        return caches + "/iogram-crash.txt"
    }

    // Вызывается в самом начале запуска приложения
    public static func start() {
        lock.lock()
        if isStarted {
            lock.unlock()
            return
        }
        isStarted = true
        lock.unlock()

        if let previous = try? String(contentsOfFile: crashFilePath, encoding: .utf8), !previous.isEmpty {
            mark("ПАДЕНИЕ В ПРОШЛЫЙ ЗАПУСК: \(previous)")
            let _ = try? FileManager.default.removeItem(atPath: crashFilePath)
        }
        let info = Bundle.main.infoDictionary
        mark("старт: \(Bundle.main.bundleIdentifier ?? "?") \(info?["CFBundleShortVersionString"] ?? "?") (\(info?["CFBundleVersion"] ?? "?")), iOS \(ProcessInfo.processInfo.operatingSystemVersionString)")

        installCrashHandlers()
        startWatchdog()
    }

    public static func mark(_ text: String) {
        let seconds = String(format: "%.2f", Date().timeIntervalSince(startedAt))
        lock.lock()
        lastMark = text
        pending.append("+\(seconds)s \(text)")
        lock.unlock()
        flush()
    }

    private static func flush() {
        lock.lock()
        if isSending || pending.isEmpty {
            lock.unlock()
            return
        }
        isSending = true
        let lines = pending
        pending.removeAll()
        lock.unlock()

        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: ["device": device, "lines": lines])
        request.timeoutInterval = 20
        URLSession.shared.dataTask(with: request) { _, _, error in
            lock.lock()
            isSending = false
            if error != nil {
                // Нет сети — вернуть строки в очередь и попробовать позже
                pending.insert(contentsOf: lines, at: 0)
                lock.unlock()
                DispatchQueue.global().asyncAfter(deadline: .now() + 3.0) {
                    flush()
                }
                return
            }
            lock.unlock()
            flush()
        }.resume()
    }

    // Раз в 2 с проверяет, отвечает ли главный поток; первые 2 минуты шлёт «жив» с последней отметкой
    private static func startWatchdog() {
        let thread = Thread {
            var reportedBlock = false
            var tick = 0
            while true {
                Thread.sleep(forTimeInterval: 2.0)
                tick += 1
                DispatchQueue.main.async {
                    lock.lock()
                    mainPingAt = Date()
                    lock.unlock()
                }
                lock.lock()
                let silence = Date().timeIntervalSince(mainPingAt)
                let last = lastMark
                lock.unlock()
                if silence > 6.0 && !reportedBlock {
                    reportedBlock = true
                    mark("ГЛАВНЫЙ ПОТОК ЗАВИС на \(Int(silence)) с; последняя отметка: \(last)")
                } else if silence < 3.0 && reportedBlock {
                    reportedBlock = false
                    mark("главный поток снова отвечает")
                }
                if tick % 5 == 0 && tick <= 60 {
                    mark("жив, главный поток молчит \(String(format: "%.1f", silence)) с; последняя отметка: \(last)")
                }
            }
        }
        thread.name = "IogramDiag"
        thread.start()
    }

    private static func installCrashHandlers() {
        NSSetUncaughtExceptionHandler { exception in
            let text = "исключение \(exception.name.rawValue): \(exception.reason ?? "")\n\(exception.callStackSymbols.prefix(40).joined(separator: "\n"))"
            let _ = try? text.write(toFile: IogramDiag.crashFilePath, atomically: true, encoding: .utf8)
        }
        for sig in [SIGABRT, SIGSEGV, SIGBUS, SIGTRAP, SIGILL, SIGFPE] {
            signal(sig) { received in
                let text = "сигнал \(received)\n\(Thread.callStackSymbols.prefix(40).joined(separator: "\n"))"
                let _ = try? text.write(toFile: IogramDiag.crashFilePath, atomically: true, encoding: .utf8)
                signal(received, SIG_DFL)
                raise(received)
            }
        }
    }
}
