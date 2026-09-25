<div align="center">
  <img src="data/installatore-apk.svg" width="96" alt="Icona Installatore Apk">
  <h1>📦 Installatore Apk</h1>
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
sudo apt install ./dist/installatore-apk_1.1.2-1_all.deb
```

L’installazione del pacchetto esegue automaticamente `postinst`: controlla GTK4, Libadwaita, ADB, il loader SVG e `aapt` e installa **solo ciò che manca davvero**, una volta sola, chiedendo la password di amministratore in quel momento. Se le dipendenze sono già tutte presenti non viene eseguito alcun `apt-get`.

**L’app non chiede mai la password di amministratore all’avvio e funziona con permessi normali.** Il launcher `/usr/bin/installatore-apk` non installa più nulla: si limita a verificare l’ambiente e, se qualcosa manca, mostra un messaggio con il comando da eseguire. Se ADB non è disponibile, la finestra si apre comunque e l’app mostra l’errore di connessione.

Dopo l’installazione, apri **Installatore Apk** dal menu delle applicazioni. Il launcher controlla l’ambiente Python, GTK4/Libadwaita e ADB, poi avvia `/usr/lib/installatore-apk/main.py` con `/usr/bin/python3`.

### 🧑‍💻 Esecuzione dalla sorgente

Installa le dipendenze su Ubuntu/Debian:

```bash
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 adb aapt xdg-utils policykit-1
```

Poi avvia l’applicazione dalla cartella del progetto:

```bash
chmod +x installatore-apk
./installatore-apk
```

Il wrapper controlla le dipendenze e avvia `main.py`; la CLI è il comando `installatore-apk`, quindi l’app si usa sempre tramite quello.

Su Fedora:

```bash
sudo dnf install python3 python3-gobject gtk4 libadwaita android-tools aapt
```

Su Arch Linux:

```bash
sudo pacman -S python python-gobject gtk4 libadwaita android-tools aapt
```

## 💻 CLI `installatore-apk`

Il comando installato è `installatore-apk` e funziona anche senza percorso: se non indica il file, l’app prende in automatico **l’unico `.apk` presente nella cartella corrente**.

```bash
installatore-apk                 # usa l'unico .apk della cartella corrente
installatore-apk /percorso/file.apk   # installa un APK specifico
```

Regole:

- nessun argomento: si usa l’unico file `.apk` della directory corrente;
- un argomento: viene usato quel percorso, relativo o assoluto;
- più di un `.apk` nella cartella corrente senza argomento: l’app si apre vuota e scegli il file con **📂 Sfoglia**;
- dalla sorgente il comando è `./installatore-apk`, che esegue lo stesso wrapper.

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

- Avvia **Installatore Apk**.
- Premi **📂 Sfoglia** e seleziona un file `.apk`.
- In alternativa, fai doppio clic sull’APK dal file manager: l’app si aprirà già con il file selezionato.
- Oppure usa la CLI `installatore-apk` descritta qui sotto.

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

### L’app non si apre dal menu

Il nuovo launcher controlla automaticamente l’ambiente grafico e tenta di installare le dipendenze mancanti. Per verificare cosa succede, esegui il launcher da terminale:

```bash
installatore-apk
```

Nessuna password di amministratore viene richiesta per usare l’app. Se ADB riporta `no permissions`, le regole udev non danno accesso al tuo utente: aggiungiti al gruppo `plugdev` **una volta sola**, poi esci e rientra nella sessione e ricollega il dispositivo.

```bash
sudo usermod -aG plugdev "$USER"
```

L’app mostra questa indicazione da sola quando rileva il caso. Dopo l’aggiornamento del pacchetto, esci dalla sessione grafica e rientra per aggiornare il menu delle applicazioni.

### `gi` non è installato

Il launcher non installa più nulla per conto tuo: indica le dipendenze mancanti e il comando da eseguire. In alternativa puoi installare manualmente i pacchetti PyGObject e le librerie GTK4:

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
xdg-mime default com.simonecompany.installatoreapk.desktop application/vnd.android.package-archive
```

### Installazione manuale dalla sorgente

1. Copia `com.simonecompany.installatoreapk.desktop` in `~/.local/share/applications/`.
2. Sostituisci i campi `Exec` e `TryExec` con il percorso assoluto del wrapper `installatore-apk` nella cartella del progetto, per esempio `Exec=/home/utente/progetto/installatore-apk %f`.
3. Copia `data/installatore-apk.svg` in `~/.local/share/icons/hicolor/scalable/apps/installatore-apk.svg`.
4. Aggiorna le cache locali:

   ```bash
   cp com.simonecompany.installatoreapk.desktop ~/.local/share/applications/
   cp data/installatore-apk.svg ~/.local/share/icons/hicolor/scalable/apps/
   chmod +x main.py installatore-apk
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
dist/installatore-apk_1.1.2-1_all.deb
```

Contenuto principale:

- `/usr/bin/installatore-apk`
- `/usr/lib/installatore-apk/main.py`
- `/usr/share/applications/com.simonecompany.installatoreapk.desktop`
- `/usr/share/icons/hicolor/scalable/apps/installatore-apk.svg`
- `/usr/share/installatore-apk/installatore-apk.svg`
- `/usr/share/installatore-apk/download.png`
- `/usr/share/doc/installatore-apk/README.md`

Il pacchetto dichiara dipendenze per Python, GTK4, Libadwaita, ADB e `policykit-1`; `aapt`/`aapt2` sono consigliati per la lettura dei metadati.

## 🗂️ Struttura del progetto

```text
.
├── main.py                       # Applicazione e logica ADB
├── installatore-apk              # Wrapper con controllo dell’ambiente
├── com.simonecompany.installatoreapk.desktop  # Launcher e integrazione MIME
├── build-deb.sh                  # Builder del pacchetto Debian
├── data/
│   ├── download.png              # Glifo di download per l’indicatore arancione
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
dpkg-deb --info dist/installatore-apk_1.1.2-1_all.deb
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
