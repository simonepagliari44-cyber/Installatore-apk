#!/bin/sh
set -eu
umask 022

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
version=1.0.5-1
package="installatore-apk_${version}_all.deb"
staging=$(mktemp -d)
chmod 0755 "$staging"
dist="$root/dist"
trap 'rm -rf "$staging"' EXIT

command -v dpkg-deb >/dev/null 2>&1
for required in main.py installatore-apk installatore-apk.desktop README.md data/installatore-apk.svg debian/control debian/postinst debian/postrm; do
    test -f "$root/$required"
done

mkdir -p "$dist"
mkdir -p "$staging/DEBIAN"
mkdir -p "$staging/usr/bin"
chmod 0755 "$staging/DEBIAN" "$staging/usr/bin"
mkdir -p "$staging/usr/lib/installatore-apk"
mkdir -p "$staging/usr/share/applications"
mkdir -p "$staging/usr/share/doc/installatore-apk"
mkdir -p "$staging/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$staging/usr/share/installatore-apk"
chmod 0755 "$staging/usr" "$staging/usr/lib" "$staging/usr/lib/installatore-apk" "$staging/usr/share" "$staging/usr/share/applications" "$staging/usr/share/doc" "$staging/usr/share/doc/installatore-apk" "$staging/usr/share/icons" "$staging/usr/share/icons/hicolor" "$staging/usr/share/icons/hicolor/scalable" "$staging/usr/share/icons/hicolor/scalable/apps" "$staging/usr/share/installatore-apk"

install -m 0755 "$root/main.py" "$staging/usr/lib/installatore-apk/main.py"
install -m 0755 "$root/installatore-apk" "$staging/usr/bin/installatore-apk"
install -m 0644 "$root/installatore-apk.desktop" "$staging/usr/share/applications/installatore-apk.desktop"
install -m 0644 "$root/README.md" "$staging/usr/share/doc/installatore-apk/README.md"
install -m 0644 "$root/data/installatore-apk.svg" "$staging/usr/share/icons/hicolor/scalable/apps/installatore-apk.svg"
install -m 0644 "$root/data/installatore-apk.svg" "$staging/usr/share/installatore-apk/installatore-apk.svg"
install -m 0644 "$root/debian/control" "$staging/DEBIAN/control"
install -m 0755 "$root/debian/postinst" "$staging/DEBIAN/postinst"
install -m 0755 "$root/debian/postrm" "$staging/DEBIAN/postrm"

dpkg-deb --root-owner-group --build "$staging" "$dist/$package"
printf '%s\n' "$dist/$package"
