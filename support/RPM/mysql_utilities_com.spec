%if 0%{?rhel} && 0%{?rhel} <= 5
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%endif

%global        doctrine mysql-fabric-doctrine-1.4.0
%global        license_type            Commercial
%global        copyright       Copyright (c) 2010, 2014, Oracle and/or its affiliates. 
%global        product_suffix      -commercial

Summary:       Collection of utilities used for maintaining and administering MySQL servers
Name:          mysql-utilities%{product_suffix}
Version:       1.4.2
Release:       1%{?dist}
License:       %{copyright} Use is subject to license terms.  Under %{license_type} license as shown in the Description field.
Group:         Development/Libraries
URL:           https://dev.mysql.com/downloads/tools/utilities/
Source0:       https://cdn.mysql.com/Downloads/MySQLGUITools/mysql-utilities-%{version}.zip
BuildArch:     noarch
BuildRequires: python-devel > 2.6
Requires:      mysql-connector-python >= 1.2.1
BuildRoot:     %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
%description

MySQL Utilities provides a collection of command-line utilities that
are used for maintaining and administering MySQL servers, including:
 o Admin Utilities (Clone, Copy, Compare, Diff, Export, Import)
 o Replication Utilities (Setup, Configuration)
 o General Utilities (Disk Usage, Redundant Indexes, Search Meta Data)
 o And many more.

This particular copy of the software is released under a commercial
license and the GNU General Public License does not apply.

%{copyright}

License information can be found in the COPYING file.

This distribution may include materials developed by third
parties. For license and attribution notices for these
materials, please refer to the documentation that accompanies
this distribution (see the "Licenses for Third-Party Components"
appendix) or view the online documentation at
<http://dev.mysql.com/doc/>

%package       extra%{product_suffix}
Summary:       Additional files for mysql-utilities
Group:         Development/Libraries

%description   extra%{product_suffix}
This package contains additional files mysql-utilities such as a MySQL
Fabric support for Doctrine Object Relational Mapper.

%prep
%setup -q
unzip data/%{doctrine}*

%build
%{__python} setup.py build

%install
rm -rf %{buildroot}

%{__python} setup.py install --skip-build --root %{buildroot}
install -d %{buildroot}%{_mandir}/man1
%{__python} setup.py install_man --root %{buildroot}

# Shipped in c/python
rm -f  %{buildroot}%{python_sitelib}/mysql/__init__.py*

# Moved to sub package
rm  %{buildroot}%{_sysconfdir}/mysql/%{doctrine}*
cp -a %{doctrine} %{buildroot}%{_datadir}/%{name}/

%clean
rm -rf %{buildroot}

%files
%defattr(-, root, root, -)
%doc CHANGES.txt LICENSE_com.txt README_com.txt
%config(noreplace) %{_sysconfdir}/mysql/fabric.cfg
%dir %{_sysconfdir}/mysql
%{_bindir}/mysqlauditadmin
%{_bindir}/mysqlauditgrep
%{_bindir}/mysqldbcompare
%{_bindir}/mysqldbcopy
%{_bindir}/mysqldbexport
%{_bindir}/mysqldbimport
%{_bindir}/mysqldiff
%{_bindir}/mysqldiskusage
%{_bindir}/mysqlfailover
%{_bindir}/mysqlfabric
%{_bindir}/mysqlfrm
%{_bindir}/mysqlindexcheck
%{_bindir}/mysqlmetagrep
%{_bindir}/mysqlprocgrep
%{_bindir}/mysqlreplicate
%{_bindir}/mysqlrpladmin
%{_bindir}/mysqlrplcheck
%{_bindir}/mysqlrplshow
%{_bindir}/mysqlserverclone
%{_bindir}/mysqlserverinfo
%{_bindir}/mysqluc
%{_bindir}/mysqluserclone
%{_bindir}/mysqlrplms
%{_bindir}/mysqlrplsync
%{python_sitelib}/mysql
%if 0%{?rhel} > 5 || 0%{?fedora} > 12
%{python_sitelib}/mysql_utilities-*.egg-info
%endif
%{_mandir}/man1/mysql*.1*

%files extra
%defattr(-, root, root, -)
%{_datadir}/%{name}

%changelog
* Wed Mar 26 2014 Balasubramanian Kandasamy <balasubramanian.kandasamy@oracle.com> - 1.4.2-1
- Updated for commercial package

* Wed Feb 26 2014  Balasubramanian Kandasamy <balasubramanian.kandasamy@oracle.com> - 1.4.2-1
- Updated for 1.4.2
- Add extra subpackage

* Fri Jan 03 2014  Balasubramanian Kandasamy <balasubramanian.kandasamy@oracle.com> - 1.3.6-1
- initial package
