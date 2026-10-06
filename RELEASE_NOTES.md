## Novità

- 🚀 Nuova CLI `installatore-apk`: senza argomenti usa l'unico file `.apk` presente nella cartella corrente.
- 🖼️ Icona dell'app nella barra in alto, con ID applicazione `com.simonecompany.installatoreapk` allineato al launcher di sistema.
- ✅ Spunta verde con «Fatto!» al termine dell'installazione.
- 🌐 Descrizioni del pacchetto localizzate in italiano, inglese, tedesco, francese, spagnolo e portoghese.
- 📱 Istruzioni per il debug USB wireless su Android 11 e successivi.

## Correzioni

- 🎨 Risolto l'indicatore di installazione: l'icona visualizzata era un simbolo del tema predefinito, non quella prevista. Ora il riquadro arancione mostra la scritta «Installa» e il pulsante è senza icona.
- 🔄 Il pulsante di aggiornamento compare solo nella schermata dell'APK.
- 🔑 Rimossa la richiesta di password di amministratore a ogni avvio: il launcher non installa più nulla e non usa più `pkexec`.
- 🔐 Dettagli e permessi dell'APK mostrati anche con Android senza librerie `aapt`/`aapt2` installate.
- 🧹 `/dist/` non viene più tracciato da git e i vecchi `.deb` vengono eliminati a ogni build.

## Permessi

L'applicazione funziona con permessi normali e non chiede mai credenziali di amministratore. Se ADB riporta `no permissions`, l'app indica il comando `sudo usermod -aG plugdev "$USER"`, da eseguire una volta sola.

## Installazione

**Debian / Ubuntu**

```bash
sudo apt install ./installatore-apk_1.1.7-1_all.deb
```

Per disinstallare:

```bash
sudo apt remove installatore-apk
```

**Fedora**

```bash
sudo dnf install python3-gobject gtk4 libadwaita android-tools librsvg2 aapt
tar -xzf installatore-apk-1.3.0-1-src.tar.gz
cd installatore-apk-1.3.0-1
./install.sh
```

Per disinstallare:

```bash
./install.sh --uninstall
```

**Arch Linux**

```bash
tar -xzf installatore-apk-1.3.0-1-src.tar.gz
cd installatore-apk-1.3.0-1
makepkg -si
```

Per disinstallare:

```bash
./install.sh --uninstall
```

`aapt` serve solo per la lettura completa dei metadati. L'app funziona con permessi normali e non chiede mai credenziali di amministratore.

📝 **Note**

Esci e rientra nella sessione grafica dopo l'aggiornamento, per aggiornare icone e menu delle applicazioni.
