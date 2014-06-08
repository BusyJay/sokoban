%define name sokoban
%define version 0.0.1a1
%define unmangled_version 0.0.1a1
%define unmangled_version 0.0.1a1
%define release 1

Summary: A project aims to ease the pain of developer synchronizing docs
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: MIT
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Jay Lee <busyjaylee@gmail.com>
requires: python>=2.7 git docker mysql mysql-server
Url: https://code.engineering.redhat.com/gerrit/gitweb?p=sokoban.git;a=summary

%description
UNKNOWN

%prep
%setup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}

%build
python setup.py build

%install
python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%post
sokoban_postinstall.sh || echo "Unable to run post job!!!
You can still run the job by command:
    sokoban_postinstall.sh"

%preun
sokoban_preuninstall.sh

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
