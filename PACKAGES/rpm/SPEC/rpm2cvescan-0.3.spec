%define debug_package %{nil}
Name: rpm2cvescanH
Version: 0.3
Release: 2.el6
Summary: RPM to cve/rhsa scanner
Packager: SecurityGuy <securityguy@fakedomain.com>
Group: Applications/System
License: GPLv2
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
Requires: rpm, perl-XML-Simple
BuildRequires: rpm-build

%description
Report what RHEL6/CentOS packages are vulnerable based on 'rpm -qa'

%prep
%setup -q

%build

%install
mkdir -p $RPM_BUILD_ROOT/localservices/sbin

install -m 0700 rpm2cvescan.pl $RPM_BUILD_ROOT/localservices/sbin/rpm2cvescan.pl
install -m 0700 rpm2cvescan-download.sh $RPM_BUILD_ROOT/localservices/sbin/rpm2cvescan-download.sh
#install -m 0700 rpmvercmp.el5 $RPM_BUILD_ROOT/localservices/sbin/rpmvercmp.el5
install -m 0700 rpmvercmp.el6 $RPM_BUILD_ROOT/localservices/sbin/rpmvercmp.el6
#install -m 0700 rpmvercmp.el7 $RPM_BUILD_ROOT/localservices/sbin/rpmvercmp.el7

%files
%defattr(-,root,root)
%doc README
%attr(0700,root,root) /localservices/sbin/rpm2cvescan.pl
%attr(0700,root,root) /localservices/sbin/rpm2cvescan-download.sh
#%attr(0700,root,root) /localservices/sbin/rpmvercmp.el5
%attr(0700,root,root) /localservices/sbin/rpmvercmp.el6
#%attr(0700,root,root) /localservices/sbin/rpmvercmp.el7

%clean
rm -rf $RPM_BUILD_ROOT

%pre

%post

%preun

%postun

%posttrans

%changelog
* Mon Jul 17 2017 SecurityGuy <securityteam@fakedomain.com> -1
- Initial build
