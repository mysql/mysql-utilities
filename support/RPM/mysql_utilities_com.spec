%define mysql_license   Commercial
%define python_version  %(python -c "import distutils.sysconfig as ds; print ds.get_python_version()")
%define name            mysql-utilities-commercial
%define version         %(python -c "import mysql.utilities as mu; print('{0}.{1}.{2}'.format(*mu.VERSION[0:3]))")
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
Source0:        %{name}-commercial%{version}-py%{python_version}.tar.gz
BuildRoot:      %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
Conflicts:      mysql-utilities

Prefix:			/usr

%description
%{release_info}

This is a release of MySQL Utilities. For the avoidance of
doubt, this particular copy of the software is released
under a commercial license and the GNU General Public
License does not apply.
MySQL Utilities is brought to you by Oracle.

%{copyright}

License information can be found in the COPYING file.

This distribution may include materials developed by third
parties. For license and attribution notices for these
materials, please refer to the documentation that accompanies
this distribution (see the "Licenses for Third-Party Components"
appendix) or view the online documentation at 
<http://dev.mysql.com/doc/>

%prep
#%setup -q -n %{name}-%{version}.linux-%{_arch}
#cp build/%{egg} %{_builddir}
#cp build/%{egg_info} %{_builddir}

%install
#rm -Rf $RPM_BUILD_ROOT
#cp -a . $RPM_BUILD_ROOT
#(cd $RPM_BUILD_ROOT ; find -follow -type f -printf "%{findpat}\n") > INSTALLED_FILES
rm -rf %{buildroot}
echo %{buildroot}
mkdir -p %{buildroot}%{python_sitelib}
mkdir -p %{buildroot}%{_mandir}
cp -a %{bdist_dir}mysql %{buildroot}%{python_sitelib}
cp -p %{bdist_dir}*.egg-info %{buildroot}%{python_sitelib}
cp -a %{bdist_dir}/scripts %{buildroot}%{_exec_prefix}/bin
cp -a %{bdist_dir}/docs %{buildroot}%{_mandir}
rm %{buildroot}%{python_sitelib}/mysql/__init__.pyc

%clean

%files
%defattr(-,root,root,-)
%doc %{bdist_dir}README.txt
%doc %{bdist_dir}LICENSE.txt
%{python_sitelib}/mysql*egg-info
%{python_sitelib}/mysql/utilities
%{_mandir}/*
%{_exec_prefix}/bin

%post
touch %{python_sitelib}/mysql/__init__.py

%postun
if [ $1 == 0 ];
then
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
* Mon Jul 29 2013 Israel Gomez <israel.gomez@oracle.com> - 1.0.0

- Initial implementation, based on Geert Vanderkelen's implementation.
