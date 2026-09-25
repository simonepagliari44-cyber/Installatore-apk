<div align="center">
  <img src="data/installatore-apk.svg" width="96" alt="Icona Installatore -apk">
  <h1>📦 Installatore -apk</h1>
  <p><strong>Installa APK sui dispositivi Android direttamente dal PC Linux.</strong></p>
  <p>Applicazione GTK4 + Libadwaita con supporto ADB, anteprima dei metadati e avvio dell’app installata.</p>
</div>

---

## ✨ Funzionalità

- 📦 Installazione di file `.apk` con `adb install -r`.
- 📱 Supporto a più dispositivi Android con selezione rapida.
- 🔍 Lettura di nome, package, versione e permessi dell’APK.
- 🖼️ Visualizzazione dell’icona dell’applicazione quando è disponibile.
- 🚀 Avvio automatico dell’app Android al termine dell’installazione.
- 🔌 Apertura diretta dei file `.apk` dal file manager.
- 🐧 Interfaccia GTK4/Libadwaita con tema chiaro o scuro del sistema.
- 📦 Pacchetto Debian `.deb` pronto da installare.
- 🧩 Fallback opzionale con `pyaxmlparser` quando `aapt`/`aapt2` non è disponibile.

## 🚀 Installazione rapida

### 📦 Pacchetto Debian

Il pacchetto installa l’app, l’icona SVG, il file `.desktop`, la documentazione e le dipendenze necessarie:

```bash
sudo apt install ./dist/installatore-apk_1.0.0-1_all.deb
```

Dopo l’installazione, apri **Installatore -apk** dal menu delle applicazioni. Il launcher utilizza automaticamente `/usr/bin/python3` e `/usr/lib/installatore-apk/main.py`.

### 🧑‍💻 Esecuzione dalla sorgente

Installa le dipendenze su Ubuntu/Debian:

```bash
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 adb aapt xdg-utils
```

Poi avvia l’applicazione dalla cartella del progetto:

```bash
python3 main.py
```

Su Fedora:

```bash
sudo dnf install python3 python3-gobject gtk4 libadwaita android-tools aapt
```

Su Arch Linux:

```bash
sudo pacman -S python python-gobject gtk4 libadwaita android-tools aapt
```

## 🧭 Come si usa

### 1. 📱 Collega il dispositivo Android

1. Attiva **Debug USB** nelle opzioni dello sviluppatore del dispositivo.
2. Collega il telefono al computer con un cavo USB.
3. Accetta l’impronta o il messaggio di autorizzazione mostrato sul telefono.
4. Verifica che il dispositivo sia visibile ad ADB:

   ```bash
   adb devices -l
   ```

5. Se compare `unauthorized`, sblocca lo schermo e accetta il messaggio di autorizzazione sul dispositivo.

### 2. 📂 Scegli un APK

- Avvia **Installatore -apk**.
- Premi **📂 Sfoglia** e seleziona un file `.apk`.
- In alternativa, fai doppio clic sull’APK dal file manager: l’app si aprirà già con il file selezionato.
- Puoi anche avviarla da terminale:

  ```bash
  python3 main.py /percorso/del/file.apk
  ```

L’app mostra il nome, il package, la versione, il percorso del file e i permessi dichiarati.

### 3. 🔌 Scegli il dispositivo

- Seleziona il dispositivo dal menu a tendina.
- Premi **🔄 Ricarica** dopo aver collegato o sbloccato un nuovo telefono.
- I dispositivi non autorizzati o non disponibili non possono ricevere l’installazione.

### 4. ⬇️ Installa l’APK

- Premi **⬇️ Installa**.
- L’app esegue:

  ```bash
  adb install -r /percorso/del/file.apk
  ```

- L’opzione `-r` tenta di conservare i dati di una versione precedente compatibile.
- Durante l’installazione puoi premere **Annulla** per interromperla.

### 5. 🚀 Avvia l’app installata

Attiva la casella **Avvia al termine** se desideri aprire automaticamente l’app sul dispositivo. L’app esegue:

```bash
adb shell monkey -p <package> -c android.intent.category.LAUNCHER 1
```

## 📡 Dispositivi Wi-Fi

L’app può usare dispositivi wireless già associati ad ADB. Il pairing non viene eseguito dall’interfaccia: configuralo una volta dal terminale con ADB.

### Android 11 e versioni successive

```bash
adb pair 192.168.1.100:37000
adb connect 192.168.1.100:5555
adb devices -l
```

Sostituisci indirizzo e porta con quelli mostrati nella sezione **Debug wireless** del telefono. Se il dispositivo non compare, verifica che computer e telefono siano sulla stessa rete.

## 🧩 Come funziona

| Fase | Operazione |
| --- | --- |
| 📖 Lettura APK | `aapt2 dump badging` o `aapt dump badging` |
| 🧩 Fallback | `pyaxmlparser`, se installato |
| 🔍 Dispositivi | `adb devices -l` |
| ⬇️ Installazione | `adb install -r` |
| 🚀 Avvio | `adb shell monkey -p <package> -c android.intent.category.LAUNCHER 1` |

L’app esegue le operazioni ADB in background e mostra lo stato nella finestra, così l’interfaccia rimane reattiva.

## 🐛 Risoluzione dei problemi

### `gi` non è installato

Installa i pacchetti PyGObject e le librerie GTK4:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
```

### ADB non viene trovato

Installa Android Platform Tools oppure imposta il percorso dell’eseguibile:

```bash
sudo apt install adb
export ADB=/percorso/assoluto/adb
python3 main.py
```

### Il dispositivo è `unauthorized`

Accetta la richiesta di autorizzazione sullo schermo del telefono. Se il problema persiste:

```bash
adb kill-server
adb start-server
adb devices -l
```

### I metadati dell’APK non possono essere letti

Installa `aapt` o `aapt2` e riprova. In alternativa, usa il fallback opzionale:

```bash
python3 -m venv --system-site-packages ~/.venvs/installatore-apk
~/.venvs/installatore-apk/bin/pip install pyaxmlparser
~/.venvs/installatore-apk/bin/python main.py /percorso/file.apk
```

### L’installazione fallisce

Controlla che:

- 🔋 il dispositivo sia autorizzato e accessibile;
- 📦 la versione dell’APK sia compatibile con quella già installata;
- 🔐 le firme dell’APK siano valide;
- 💾 ci sia spazio sufficiente sul dispositivo;
- ⚙️ il debug USB o wireless sia abilitato.

## 🖼️ Integrazione con il file manager

Il pacchetto Debian registra automaticamente l’associazione per `application/vnd.android.package-archive`. Se il file manager non la imposta automaticamente:

```bash
xdg-mime default installatore-apk.desktop application/vnd.android.package-archive
```

### Installazione manuale dalla sorgente

1. Copia `installatore-apk.desktop` in `~/.local/share/applications/`.
2. Sostituisci nel campo `Exec` il percorso `/usr/lib/installatore-apk/main.py` con il percorso assoluto del tuo `main.py`.
3. Copia `data/installatore-apk.svg` in `~/.local/share/icons/hicolor/scalable/apps/installatore-apk.svg`.
4. Aggiorna le cache locali:

   ```bash
   cp installatore-apk.desktop ~/.local/share/applications/
   cp data/installatore-apk.svg ~/.local/share/icons/hicolor/scalable/apps/
   chmod +x main.py
   update-desktop-database ~/.local/share/applications 2>/dev/null || true
   gtk4-update-icon-cache -q -t -f ~/.local/share/icons/hicolor 2>/dev/null || gtk-update-icon-cache -q -t -f ~/.local/share/icons/hicolor 2>/dev/null || true
   ```

## 📦 Costruire il pacchetto `.deb`

Il repository include uno script riproducibile che usa `dpkg-deb`:

```bash
chmod +x build-deb.sh
./build-deb.sh
```

Il pacchetto generato sarà:

```text
dist/installatore-apk_1.0.0-1_all.deb
```

Contenuto principale:

- `/usr/lib/installatore-apk/main.py`
- `/usr/share/applications/installatore-apk.desktop`
- `/usr/share/icons/hicolor/scalable/apps/installatore-apk.svg`
- `/usr/share/doc/installatore-apk/README.md`

Il pacchetto dichiara dipendenze per Python, GTK4, Libadwaita, ADB e `aapt`/`aapt2`.

## 🗂️ Struttura del progetto

```text
.
├── main.py                       # Applicazione e logica ADB
├── installatore-apk.desktop      # Launcher e integrazione MIME
├── build-deb.sh                  # Builder del pacchetto Debian
├── data/
│   └── installatore-apk.svg      # Icona vettoriale dell’app
├── debian/
│   ├── changelog                 # Versione del pacchetto
│   ├── control                   # Metadati e dipendenze
│   ├── postinst                  # Aggiornamento cache dopo installazione
│   └── postrm                    # Pulizia cache dopo rimozione
├── dist/                         # Pacchetto .deb generato
└── README.md
```

## 🛠️ Controlli di sviluppo

Prima di pubblicare modifiche, esegui:

```bash
flake8 main.py
mypy main.py
python3 -m py_compile main.py
```

Per ricostruire il pacchetto dopo ogni modifica:

```bash
./build-deb.sh
dpkg-deb --info dist/installatore-apk_1.0.0-1_all.deb
```

## ⚠️ Note operative

- 🔐 L’app usa ADB e non richiede root sul computer.
- 📱 Il debug USB/wireless deve essere abilitato esplicitamente sul dispositivo.
- 🔄 Se cambi dispositivo, usa **Ricarica** prima di installare.
- 🧠 I permessi visualizzati sono quelli dichiarati nell’APK; Android può richiedere ulteriori autorizzazioni dopo l’installazione.
- 🗑️ Per disinstallare il pacchetto:

  ```bash
  sudo apt remove installatore-apk
  ```

<div align="center">
  <p>✨ Realizzato con Python, GTK4, Libadwaita e ADB ✨</p>
</div>
