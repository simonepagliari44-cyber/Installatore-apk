# Maintainer: Installatore Apk contributors
# This file is part of the installatore-apk project.
# Builds a native Arch Linux package from the sources in this directory.

pkgname=installatore-apk
pkgver=1.3.0
pkgrel=1
pkgdesc="Installatore Apk per Android via ADB"
arch=('any')
url="https://github.com/simonepagliari44-cyber/Installatore-apk"
license=('MIT')
depends=(
    'python3'
    'python-gobject'
    'gtk4'
    'libadwaita'
    'android-tools'
    'librsvg'
)
optdepends=('aapt2: lettura completa dei metadati dell APK')
provides=("$pkgname")
conflicts=()
source=()
sha256sums=()

prepare() {
    install -Dm755 main.py "$srcdir/ir/$pkgname/main.py"
    install -Dm755 installatore-apk "$srcdir/ir/$pkgname/installatore-apk"
    install -Dm644 com.simonecompany.installatoreapk.desktop \
        "$srcdir/ir/$pkgname/com.simonecompany.installatoreapk.desktop"
    install -Dm644 data/installatore-apk.svg \
        "$srcdir/ir/$pkgname/installatore-apk.svg"
    install -Dm644 README.md "$srcdir/ir/$pkgname/README.md"
    printf '%s\n' "$pkgver-$pkgrel" > "$srcdir/ir/$pkgname/VERSION"
}

package() {
    install -Dm755 "$srcdir/ir/$pkgname/installatore-apk" \
        "$pkgdir/usr/bin/installatore-apk"
    install -Dm755 "$srcdir/ir/$pkgname/main.py" \
        "$pkgdir/usr/lib/installatore-apk/main.py"
    install -Dm644 "$srcdir/ir/$pkgname/VERSION" \
        "$pkgdir/usr/lib/installatore-apk/VERSION"
    install -Dm644 "$srcdir/ir/$pkgname/com.simonecompany.installatoreapk.desktop" \
        "$pkgdir/usr/share/applications/com.simonecompany.installatoreapk.desktop"
    install -Dm644 "$srcdir/ir/$pkgname/installatore-apk.svg" \
        "$pkgdir/usr/share/icons/hicolor/scalable/apps/installatore-apk.svg"
    install -Dm644 "$srcdir/ir/$pkgname/installatore-apk.svg" \
        "$pkgdir/usr/share/installatore-apk/installatore-apk.svg"
    install -Dm644 "$srcdir/ir/$pkgname/README.md" \
        "$pkgdir/usr/share/doc/$pkgname/README.md"
}
