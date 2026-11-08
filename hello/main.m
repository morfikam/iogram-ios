// Проверка подписи GBox: один экран с результатами и отметка на сервере IOGRAM.
// Запустилось — подпись работает и причина чёрного экрана в сборке Telegram; не запустилось — в подписи.
#import <UIKit/UIKit.h>
#import <Security/Security.h>
#import <dlfcn.h>

static NSString *const kDiagUrl = @"https://iogram.iogram-server.workers.dev/diag";

static void SendMark(NSString *line, void (^done)(BOOL isOk)) {
    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:[NSURL URLWithString:kDiagUrl]];
    request.HTTPMethod = @"POST";
    request.timeoutInterval = 15.0;
    [request setValue:@"application/json" forHTTPHeaderField:@"Content-Type"];
    request.HTTPBody = [NSJSONSerialization dataWithJSONObject:@{ @"device": @"hello", @"lines": @[ line ] } options:0 error:nil];
    [[[NSURLSession sharedSession] dataTaskWithRequest:request completionHandler:^(NSData *data, NSURLResponse *response, NSError *error) {
        if (done) done(error == nil);
    }] resume];
}

static NSString *ProbeKeychain(void) {
    NSDictionary *query = @{
        (__bridge id)kSecClass: (__bridge id)kSecClassGenericPassword,
        (__bridge id)kSecAttrAccount: @"iogramHelloProbe",
        (__bridge id)kSecAttrService: @"",
        (__bridge id)kSecReturnAttributes: @YES,
    };
    CFTypeRef found = NULL;
    OSStatus status = SecItemCopyMatching((__bridge CFDictionaryRef)query, &found);
    if (status == errSecItemNotFound) status = SecItemAdd((__bridge CFDictionaryRef)query, &found);
    if (found != NULL) CFRelease(found);
    return status == errSecSuccess ? @"работает" : [NSString stringWithFormat:@"ошибка %d", (int)status];
}

static NSString *ProbeFramework(void) {
    NSString *path = [[NSBundle mainBundle].privateFrameworksPath stringByAppendingPathComponent:@"IogramTestKit.framework/IogramTestKit"];
    void *handle = dlopen(path.fileSystemRepresentation, RTLD_NOW);
    if (handle == NULL) return [NSString stringWithFormat:@"НЕ загрузилась: %s", dlerror()];
    int (*kitValue)(void) = dlsym(handle, "iogram_test_kit");
    return kitValue != NULL && kitValue() == 42 ? @"загрузилась" : @"загрузилась, но функции нет";
}

static NSString *BuildReport(void) {
    NSBundle *bundle = [NSBundle mainBundle];
    NSString *bundleId = bundle.bundleIdentifier ?: @"?";
    NSURL *groupUrl = [[NSFileManager defaultManager] containerURLForSecurityApplicationGroupIdentifier:[@"group." stringByAppendingString:bundleId]];
    return [NSString stringWithFormat:@"iOS %@\nИмя пакета: %@\nОбщая папка: %@\nСвязка ключей: %@\nБиблиотека: %@",
        [UIDevice currentDevice].systemVersion, bundleId, groupUrl != nil ? @"есть" : @"НЕТ", ProbeKeychain(), ProbeFramework()];
}

@interface AppDelegate : UIResponder <UIApplicationDelegate>
@property (nonatomic, strong) UIWindow *window;
@end

@implementation AppDelegate
- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)launchOptions {
    NSString *report = BuildReport();
    UIViewController *controller = [[UIViewController alloc] init];
    controller.view.backgroundColor = [UIColor colorWithRed:0.15 green:0.55 blue:0.30 alpha:1.0];
    UILabel *label = [[UILabel alloc] initWithFrame:CGRectInset(controller.view.bounds, 24.0, 80.0)];
    label.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    label.numberOfLines = 0;
    label.textColor = [UIColor whiteColor];
    label.font = [UIFont systemFontOfSize:20.0];
    label.text = [NSString stringWithFormat:@"Iogram Test запустился\n\n%@\n\nСервер: проверяю…", report];
    [controller.view addSubview:label];

    self.window = [[UIWindow alloc] initWithFrame:[UIScreen mainScreen].bounds];
    self.window.rootViewController = controller;
    [self.window makeKeyAndVisible];

    SendMark([NSString stringWithFormat:@"экран показан: %@", [report stringByReplacingOccurrencesOfString:@"\n" withString:@"; "]], ^(BOOL isOk) {
        dispatch_async(dispatch_get_main_queue(), ^{
            label.text = [NSString stringWithFormat:@"Iogram Test запустился\n\n%@\n\nСервер: %@", report, isOk ? @"отметка ушла" : @"НЕТ связи"];
        });
    });
    return YES;
}
@end

int main(int argc, char *argv[]) {
    @autoreleasepool {
        SendMark(@"main: процесс запущен", nil);
        return UIApplicationMain(argc, argv, nil, NSStringFromClass([AppDelegate class]));
    }
}
