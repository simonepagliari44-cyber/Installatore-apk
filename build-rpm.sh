#!/bin/sh
set -eu
umask 022

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
name="installatore-apk"
version=$(sed -n 's/^version=//p' "$root/build-deb.sh")
topdir=${RPMBUILD_TOPDIR:-$HOME/rpmbuild}
staging="$root/.rpmbuild"
archive="$name-$version.tar.gz"
dist="$root/dist"

command -v rpmbuild >/dev/null 2>&1 || {
    printf '%s\n' "rpmbuild non è installato (Fedora: sudo dnf install rpm-build)" >&2
    exit 1
}

rm -rf "$staging"
mkdir -p "$staging/$name-$version"
mkdir -p "$topdir/SOURCES" "$topdir/SPECS" "$topdir/BUILD" \
    "$topdir/BUILDROOT" "$topdir/RPMS" "$topdir/SRPS" "$dist"

for required in main.py installatore-apk com.simonecompany.installatoreapk.desktop data/installatore-apk.svg README.md; do
    test -f "$root/$required"
done

mkdir -p "$staging/$name-$version/data"
cp "$root/main.py" "$staging/$name-$version/main.py"
cp "$root/installatore-apk" "$staging/$name-$version/installatore-apk"
cp "$root/com.simonecompany.installatoreapk.desktop" \
    "$staging/$name-$version/com.simonecompany.installatoreapk.desktop"
cp "$root/README.md" "$staging/$name-$version/README.md"
cp "$root/data/installatore-apk.svg" "$staging/$name-$version/data/installatore-apk.svg"

tar -czf "$topdir/SOURCES/$archive" -C "$staging" "$name-$version"
cp "$root/installatore-apk.spec" "$topdir/SPECS/installatore-apk.spec"
rm -rf "$dist"/installatore-apk-*.rpm

rpmbuild --define "_topdir $topdir" --define "_rpmdir $dist" \
    -bb "$topdir/SPECS/installatore-apk.spec"

rm -rf "$staging"
printf '%s\n' "$dist"
