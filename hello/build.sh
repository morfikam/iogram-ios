#!/bin/bash
# Собирает IogramTest.ipa тем же Xcode, что и Telegram
set -euo pipefail
cd "$(dirname "$0")"

SDK=$(xcrun --sdk iphoneos --show-sdk-path)
CC=(xcrun --sdk iphoneos clang -arch arm64 -miphoneos-version-min=13.0 -isysroot "$SDK")
APP=build/Payload/IogramTest.app
KIT="$APP/Frameworks/IogramTestKit.framework"

rm -rf build
mkdir -p "$KIT"

"${CC[@]}" -dynamiclib -install_name @rpath/IogramTestKit.framework/IogramTestKit -o "$KIT/IogramTestKit" kit.c
plutil -create xml1 "$KIT/Info.plist"
plutil -insert CFBundleExecutable -string IogramTestKit "$KIT/Info.plist"
plutil -insert CFBundleIdentifier -string com.iogram.hello.kit "$KIT/Info.plist"
plutil -insert CFBundlePackageType -string FMWK "$KIT/Info.plist"
plutil -insert CFBundleShortVersionString -string 1.0 "$KIT/Info.plist"
plutil -insert CFBundleVersion -string 1 "$KIT/Info.plist"
plutil -convert binary1 "$KIT/Info.plist"

"${CC[@]}" -fobjc-arc -framework UIKit -framework Foundation -framework Security \
  -Wl,-rpath,@executable_path/Frameworks -o "$APP/IogramTest" main.m

cp Info.plist "$APP/Info.plist"
plutil -lint "$APP/Info.plist"
plutil -convert binary1 "$APP/Info.plist"
python3 make-icon.py "$APP/AppIcon60x60@2x.png"
printf 'APPL????' > "$APP/PkgInfo"

codesign -f -s - "$KIT"
codesign -f -s - "$APP"
codesign --verify --deep "$APP"

(cd build && zip -qry IogramTest.ipa Payload)
lipo -info "$APP/IogramTest"
otool -l "$APP/IogramTest" | grep -A4 LC_BUILD_VERSION
unzip -l build/IogramTest.ipa
