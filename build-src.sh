#!/bin/sh
set -eu
umask 022

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
name="installatore-apk"
version=$(sed -n 's/^version=//p' "$root/build-deb.sh")
dist="$root/dist"
staging="$root/.srcbuild"
archive="$dist/$name-$version-src.tar.gz"

command -v tar >/dev/null 2>&1

files="main.py installatore-apk com.simonecompany.installatoreapk.desktop README.md PKGBUILD"
for required in $files data/installatore-apk.svg; do
    test -f "$root/$required"
done

rm -rf "$staging"
mkdir -p "$staging/$name-$version/data" "$dist"
cp "$root/main.py" "$staging/$name-$version/main.py"
cp "$root/installatore-apk" "$staging/$name-$version/installatore-apk"
cp "$root/com.simonecompany.installatoreapk.desktop" \
    "$staging/$name-$version/com.simonecompany.installatoreapk.desktop"
cp "$root/README.md" "$staging/$name-$version/README.md"
cp "$root/PKGBUILD" "$staging/$name-$version/PKGBUILD"
cp "$root/data/installatore-apk.svg" \
    "$staging/$name-$version/data/installatore-apk.svg"

rm -f "$dist"/"$name"-*-src.tar.gz
tar -czf "$archive" -C "$staging" "$name-$version"
rm -rf "$staging"
printf '%s\n' "$archive"
