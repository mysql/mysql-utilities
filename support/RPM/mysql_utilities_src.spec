%define mysql_license   GPLv2
%define python_version  %(python -c "import distutils.sysconfig as ds; print ds.get_version()")
%define name            mysql-utilities
%define summary         MySQL Utilities contain a collection of scripts useful for managing and administering MySQL servers
%define vendor          Oracle
%define packager        Oracle and/or its affiliates Product Engineering Team <mysql-build@oss.oracle.com>
%define copyright       Copyright (c) 2010, 2014, Oracle and/or its affiliates. All rights reserved.

# Following are given defined from the environment/command line:
#  version
#  release_info
#  _topdir

%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from %distutils.sysconfig import get_python_lib; print (get_python_lib())")}

Name:           %{name}
Version:        %{version}
Release:        1%{?dist}
Summary:        %{summary}

Group:          Development/Libraries
License:        %{copyright} Use is subject to license terms.  Under %{mysql_license} license as shown in the Description field.
Vendor:         %{vendor}
Packager:       %{packager}
URL:            http://dev.mysql.com/downloads/

BuildRoot:      %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch:      noarch
Source0:        %{name}-%{version}.tar.gz
#BuildRequires:  python >= 2.6
Requires:       python >= 2.6, mysql-connector-python >= 1.0.9
Obsoletes:      %{name} <= %{version}, %{name}-commercial <= %{version}, 
Provides:       %{name} = %{version}
AutoReq:        no
Conflicts:      %{name}-commercial

%description
%{release_info}

This is a release of MySQL Utilities. For the avoidance of
doubt, this particular copy of the software is released
under the version 2 of the GNU General Public License.
MySQL Utilities is brought to you by Oracle.

%{copyright}

License information can be found in the COPYING file.

MySQL FOSS License Exception
We want free and open source software applications under
certain licenses to be able to use the GPL-licensed MySQL
Utilities (specified GPL-licensed MySQL client libraries)
despite the fact that not all such FOSS licenses are
compatible with version 2 of the GNU General Public License.
Therefore there are special exceptions to the terms and
conditions of the GPLv2 as applied to these client libraries,
which are identified and described in more detail in the
FOSS License Exception at
<http://www.mysql.com/about/legal/licensing/foss-exception.html>

This software is OSI Certified Open Source Software.
OSI Certified is a certification mark of the Open Source Initiative.

This distribution may include materials developed by third
parties. For license and attribution notices for these
materials, please refer to the documentation that accompanies
this distribution (see the "Licenses for Third-Party Components"
appendix) or view the online documentation at
<http://dev.mysql.com/doc/>
A copy of the license/notices is also reproduced below.

GPLv2 Disclaimer
For the avoidance of doubt, except that if any license choice
other than GPL or LGPL is available it will apply instead,
Oracle elects to use only the General Public License version 2
(GPLv2) at this time for any software where a choice of GPL
license versions is made available with the language indicating
that GPLv2 or any later version may be used, or where a choice
of which version of the GPL is applied is otherwise unspecified.

%prep
%setup -n %{name}-%{version}

%build
python setup.py build
python setup.py build_scripts
python setup.py install_egg_info -d .

%install
python setup.py install -O1 --root=$RPM_BUILD_ROOT --prefix=%{_prefix} \
	--record=INSTALLED_FILES \
	install_man --prefix=%{_mandir}

mkdir %{buildroot}%{_docdir}/
mkdir %{buildroot}%{_docdir}/%{name}-%{version}/
cp -p README.txt %{buildroot}%{_docdir}/%{name}-%{version}/
cp -p LICENSE.txt %{buildroot}%{_docdir}/%{name}-%{version}/
# Removing the shared __init__.py[c] file(s), recreated in %post
TMP=`grep 'mysql/__init__.py' INSTALLED_FILES | head -n1`
PKGLOC=`dirname $TMP`
sed -i '/mysql\/__init__.py/d' INSTALLED_FILES
rm $RPM_BUILD_ROOT$PKGLOC/__init__.py* 2>/dev/null 1>&2

%clean
rm -rf ${buildroot}

%files -f INSTALLED_FILES
%defattr(-,root,root)
%doc %{_docdir}/%{name}-%{version}/README.txt
%doc %{_docdir}/%{name}-%{version}/LICENSE.txt
%{_mandir}/man1/mysqlauditadmin.1*
%{_mandir}/man1/mysqlauditgrep.1*
%{_mandir}/man1/mysqldbcompare.1*
%{_mandir}/man1/mysqldbcopy.1*
%{_mandir}/man1/mysqldbexport.1*
%{_mandir}/man1/mysqldbimport.1*
%{_mandir}/man1/mysqldiff.1*
%{_mandir}/man1/mysqldiskusage.1*
%{_mandir}/man1/mysqlfailover.1*
%{_mandir}/man1/mysqlindexcheck.1*
%{_mandir}/man1/mysqlmetagrep.1*
%{_mandir}/man1/mysqlprocgrep.1*
%{_mandir}/man1/mysqlreplicate.1*
%{_mandir}/man1/mysqlrpladmin.1*
%{_mandir}/man1/mysqlrplcheck.1*
%{_mandir}/man1/mysqlrplshow.1*
%{_mandir}/man1/mysqlserverclone.1*
%{_mandir}/man1/mysqlserverinfo.1*
%{_mandir}/man1/mysqluc.1*
%{_mandir}/man1/mysqluserclone.1*

%post
touch %{python_sitelib}/mysql/__init__.py

%postun
if [ $1 == 0 ];
then
    # Non empty directories will be left alone
    rmdir %{python_sitelib}/mysql/utilities/common
    rmdir %{python_sitelib}/mysql/utilities/command
    rmdir %{python_sitelib}/mysql/utilities

    # Try to remove the MySQL top package mysql/
    SUBPKGS=`ls --ignore=*.py{c,o} -m %{python_sitelib}/mysql`
    if [ "$SUBPKGS" == "__init__.py" ];
    then
        rm %{python_sitelib}/mysql/__init__.py* 2>/dev/null 1>&2
        # This should not fail, but show error if any
        rmdir %{python_sitelib}/mysql/
    fi

    exit 0
fi

%changelog
* Fri Oct 12 2012 Geert Vanderkelen <geert.vanderkelen@oracle.com> - 1.2.0

- Initial implementation.
