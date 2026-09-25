%global app_id com.simonecompany.installatoreapk
%global app_name installatore-apk

Name:           %{app_name}
Version:        1.2.0
Release:        1%{?dist}
Summary:        Installatore Apk per Android via ADB
License:        MIT
URL:            https://github.com/simonepagliari44-cyber/Installatore-apk
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
Requires:       python3
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       android-tools
Requires:       librsvg2
Recommends:     aapt
Recommends:     aapt2

%description
Installatore Apk installs APK files on Android devices over ADB, with both
USB and Wi-Fi (wireless debugging) support. It reads the APK metadata,
shows the requested permissions, installs the package and can launch it
right after.

The application runs with regular user permissions and never asks for
administrator authentication.

%prep
%setup -q -n %{name}-%{version}

%build

%install
rm -rf %{buildroot}
install -Dm755 installatore-apk %{buildroot}%{_bindir}/%{app_name}
install -Dm755 main.py %{buildroot}%{_datadir}/%{app_name}/main.py
printf '%%{version}-%%{release}\n' > %{buildroot}%{_datadir}/%{app_name}/VERSION
install -Dm644 com.simonecompany.installatoreapk.desktop \
    %{buildroot}%{_datadir}/applications/%{app_id}.desktop
install -Dm644 data/installatore-apk.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/%{app_name}.svg
install -Dm644 data/installatore-apk.svg \
    %{buildroot}%{_datadir}/%{app_name}/installatore-apk.svg
install -Dm644 README.md %{buildroot}%{_datadir}/doc/%{app_name}/README.md

%files
%doc %{_datadir}/doc/%{app_name}/README.md
%{_bindir}/%{app_name}
%{_datadir}/%{app_name}
%{_datadir}/applications/%{app_id}.desktop
%{_datadir}/icons/hicolor/scalable/apps/%{app_name}.svg

%changelog
* Fri Sep 25 2026 Installatore Apk contributors - 1.2.0-1
- Add Arch Linux (PKGBUILD) and Fedora (RPM spec) packaging.
- Show the "Installa" label in the orange box and drop the download icon.
- Remove the icon-theme lookup for the install indicator.
- Stop asking for administrator authentication on every launch.
- Show the running version in the window.
- Add the installatore-apk CLI.
