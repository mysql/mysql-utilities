%define mysql_license   GPLv2
%define python_version  %(python -c "import distutils.sysconfig as ds; print ds.get_version()")
%define name            mysql-utilities
%define summary         MySQL Utilities contain a collection of scripts useful for managing and administering MySQL servers
%define vendor          Oracle
%define packager        Oracle and/or its affiliates Product Engineering Team <mysql-build@oss.oracle.com>
%define copyright       Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.

# Following are given defined from the environment/command line:
#  version
#  release_info
#  _topdir

# Hack to use a pattern using %P in the find command
%define findpat %( echo "/%""P" )

# Prevent manual pages to be compressed (also does not strip binaries, etc.)
%global __os_install_post %{nil}

Name:           %{name}
Version:        %{version}
Release:        1%{?dist}
Summary:        %{summary}

Group:          Development/Libraries
License:        %{copyright} Use is subject to license terms.  Under %{mysql_license} license as shown in the Description field.
Vendor:         %{vendor}
Packager:       %{packager}
URL:            http://dev.mysql.com/downloads/
Source0:		%{name}-%{version}.linux-%{_arch}.tar.gz
BuildRoot:      %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
Conflicts:      mysql-utilities-com

Prefix:			/usr

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
%setup -q -n %{name}-%{version}.linux-%{_arch}

%install
rm -Rf $RPM_BUILD_ROOT
cp -a . $RPM_BUILD_ROOT
(cd $RPM_BUILD_ROOT ; find -follow -type f -printf "%{findpat}\n") > INSTALLED_FILES

%clean

%files -f INSTALLED_FILES
%defattr(-,root,root)

%changelog
* Fri Feb  1 2013 Geert Vanderkelen <geert.vanderkelen@oracle.com> - 1.3.0

- Initial implementation.
