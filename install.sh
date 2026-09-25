#!/bin/sh
set -eu

name="installatore-apk"
app_id="com.simonecompany.installatoreapk"
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

action="install"
case "${1:-}" in
    --uninstall|-u) action="uninstall" ;;
    --help|-h)
        cat <<'HELP'
Uso: ./install.sh [--uninstall]

  install.sh              installa l'applicazione in /usr
  install.sh --uninstall  rimuove l'applicazione
  install.sh --help       mostra questo messaggio

Le dipendenze (python3-gobject, gtk4, libadwaita, android-tools) vanno
installate con il gestore pacchetti prima di eseguire questo script.
HELP
        exit 0
        ;;
    "") ;;
    *) printf '%s\n' "Opzione sconosciuta: $1 (prova --help)" >&2; exit 2 ;;
esac

prefix=${PREFIX:-/usr}
bindir="$prefix/bin"
datadir="$prefix/share"
appdir="$datadir/$name"

if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        exec sudo env "PREFIX=$prefix" "$0" "$@"
    fi
    printf '%s\n' "Servono i permessi di amministratore. Esegui con sudo." >&2
    exit 1
fi

missing=""
for file in main.py installatore-apk "$app_id.desktop" data/installatore-apk.svg; do
    if [ ! -f "$script_dir/$file" ]; then
        missing="$missing $file"
    fi
done
if [ -n "$missing" ] && [ "$action" = "install" ]; then
    printf '%s\n' "Archivio incompleto, mancano:$missing" >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' "python3 non è installato." >&2
    exit 1
fi

version="1.3.0-1"
if [ -f "$script_dir/VERSION" ]; then
    version=$(cat "$script_dir/VERSION")
fi

refresh_caches() {
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q "$datadir/applications" 2>/dev/null || true
    fi
    if command -v gtk4-update-icon-cache >/dev/null 2>&1; then
        gtk4-update-icon-cache -q -t -f "$datadir/icons/hicolor" 2>/dev/null || true
    elif command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q -t -f "$datadir/icons/hicolor" 2>/dev/null || true
    fi
}

case "$action" in
    install)
        install -d -m 0755 "$bindir"
        install -d -m 0755 "$appdir"
        install -d -m 0755 "$datadir/applications"
        install -d -m 0755 "$datadir/icons/hicolor/scalable/apps"
        install -m 0755 "$script_dir/main.py" "$appdir/main.py"
        install -m 0755 "$script_dir/installatore-apk" "$bindir/$name"
        install -m 0644 "$script_dir/$app_id.desktop" \
            "$datadir/applications/$app_id.desktop"
        install -m 0644 "$script_dir/data/installatore-apk.svg" \
            "$datadir/icons/hicolor/scalable/apps/$name.svg"
        install -m 0644 "$script_dir/data/installatore-apk.svg" \
            "$appdir/installatore-apk.svg"
        printf '%s\n' "$version" > "$appdir/VERSION"
        if [ -f "$script_dir/README.md" ]; then
            install -d -m 0755 "$datadir/doc/$name"
            install -m 0644 "$script_dir/README.md" "$datadir/doc/$name/README.md"
        fi
        refresh_caches
        printf '%s\n' "Installatore Apk $version installato in $prefix."
        printf '%s\n' "Apri l'applicazione dal menu, oppure esegui: $name"
        ;;
    uninstall)
        rm -f "$bindir/$name"
        rm -f "$datadir/applications/$app_id.desktop"
        rm -f "$datadir/icons/hicolor/scalable/apps/$name.svg"
        rm -rf "$appdir"
        rm -rf "$datadir/doc/$name"
        refresh_caches
        printf '%s\n' "Installatore Apk rimosso."
        ;;
esac
