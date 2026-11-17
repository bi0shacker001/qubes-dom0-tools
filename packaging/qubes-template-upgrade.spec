Name:           qubes-template-upgrade
Version:        0.1.0
Release:        1%{?dist}
Summary:        Upgrade customized Fedora templates in Qubes OS
License:        GPL-2.0-only
URL:            https://github.com/bi0shacker001/qubes-dom0-tools
Source0:        qubes-template-upgrade.py
Source1:        LICENSE
BuildArch:      noarch
Requires:       python3-qubesadmin
Requires:       /usr/bin/qvm-clone
Requires:       /usr/bin/qvm-run
Requires:       /usr/bin/qvm-shutdown

%description
Clone, upgrade, and validate a customized Fedora TemplateVM, then migrate
selected AppVMs with an assignment rollback journal.

%install
install -Dpm 0755 %{SOURCE0} %{buildroot}%{_bindir}/qubes-template-upgrade
install -pm 0644 %{SOURCE1} LICENSE

%files
%license LICENSE
%{_bindir}/qubes-template-upgrade
