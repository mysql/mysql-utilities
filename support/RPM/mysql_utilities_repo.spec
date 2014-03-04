%if 0%{?rhel} && 0%{?rhel} <= 5
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%endif

Summary:       Collection of utilities used for maintaining and administering MySQL servers
Name:          mysql-utilities
Version:       1.4.2
Release:       1%{?dist}
License:       GPLv2
Group:         Development/Libraries
URL:           https://dev.mysql.com/downloads/tools/utilities/
Source0:       https://cdn.mysql.com/Downloads/MySQLGUITools/mysql-utilities-%{version}.zip
BuildArch:     noarch
BuildRequires: python-devel > 2.6
Requires:      mysql-connector-python >= 1.0.9
BuildRoot:     %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
%description

MySQL Utilities provides a collection of command-line utilities that
are used for maintaining and administering MySQL servers, including:
 o Admin Utilities (Clone, Copy, Compare, Diff, Export, Import)
 o Replication Utilities (Setup, Configuration)
 o General Utilities (Disk Usage, Redundant Indexes, Search Meta Data)
 o And many more.

%prep
%setup -q

%build
%{__python} setup.py build

%install
rm -rf %{buildroot}

%{__python} setup.py install --skip-build --root %{buildroot}
install -d %{buildroot}%{_mandir}/man1
%{__python} setup.py install_man --root %{buildroot}

# Shipped in c/python
rm -f  %{buildroot}%{python_sitelib}/mysql/__init__.py*

# Including fabric config
if [ -d %{bdist_dir}/etc ];
then
    cp -a %{bdist_dir}/etc %{buildroot}
fi
touch ETC
if [ -d %{buildroot}/etc ];
then
    echo "/etc/mysql" > ETC
fi

%clean
rm -rf %{buildroot}

%files -f ETC
%defattr(-, root, root, -)
%doc CHANGES.txt LICENSE.txt README.txt
%{_bindir}/
%{python_sitelib}/mysql
%if 0%{?rhel} > 5 || 0%{?fedora} > 12
%{python_sitelib}/mysql_utilities-*.egg-info
%endif
%{_mandir}/man1/mysql*.1*


%changelog
* Tue Mar 04 2014  Israel Gomez <israel.gomez@oracle.com> - 1.4.2-1
- Updated to include Fabric project

* Fri Jan 03 2014  Balasubramanian Kandasamy <balasubramanian.kandasamy@oracle.com> - 1.3.6-1
- initial package
