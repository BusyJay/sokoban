from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend, RemoteUserBackend
try:
    import kerberos
except ImportError:
    kerberos = None
from django.core.validators import email_re

__author__ = 'jay'


class SimpleBackend(ModelBackend):
    # The source code is based on: http://www.djangosnippets.org/snippets/74/
    # All rights reserved by the orignal authors.
    """
    Email authorization backend for TCMS.
    """
    # Web UI Needed
    can_login = True
    can_register = True
    can_logout = True

    def authenticate(self, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
            # If username is an email address, then try to pull it up
        if email_re.search(username):
            try:
                user = UserModel.objects.get(email=username)
            except UserModel.DoesNotExist:
                return None
        else:
            # We have a non-email address username we should try username
            try:
                user = UserModel.objects.get(username=username)
            except UserModel.DoesNotExist:
                return None
        if user.check_password(password):
            return user


class KerberosBackend(ModelBackend):
    """
    Kerberos authorization backend for TCMS.

    Required python-kerberos backend, correct /etc/krb5.conf file,
    And correct KRB5_REALM settings in settings.py.

    Example in settings.py:
    # Kerberos settings
    KRB5_REALM = 'REDHAT.COM'
    """
    # Web UI Needed
    can_login = True
    can_register = False
    can_logout = True

    def authenticate(self, username=None, password=None, **kwargs):
        if not kerberos:
            return None
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        try:
            kerberos.checkPassword(
                username, password, '',
                settings.KRB5_REALM
            )
        except kerberos.BasicAuthError:
            return None

        try:
            user = UserModel.objects.get(username=username)
        except UserModel.DoesNotExist:
            user = UserModel.objects.create_user(
                username=username,
                email='%s@%s' % (username, settings.KRB5_REALM.lower())
            )

        user.set_unusable_password()
        user.save()
        return user


class ModAuthKerbBackend(RemoteUserBackend):
    """
    mod_auth_kerb modules authorization backend for TCMS.
    Based on DjangoRemoteUser backend.

    Required correct /etc/krb5.conf, /etc/krb5.keytab and
    Correct mod_auth_krb5 module settings for apache.

    Example apache settings:

    # Set a httpd config to protect krb5login page with kerberos.
    # You need to have mod_auth_kerb installed to use kerberos auth.
    # Httpd config /etc/httpd/conf.d/<project>.conf should look like this:

    <Location "/">
        SetHandler python-program
        PythonHandler django.core.handlers.modpython
        SetEnv DJANGO_SETTINGS_MODULE <project>.settings
        PythonDebug On
    </Location>

    <Location "/auth/krb5login">
        AuthType Kerberos
        AuthName "<project> Kerberos Authentication"
        KrbMethodNegotiate on
        KrbMethodK5Passwd off
        KrbServiceName HTTP
        KrbAuthRealms EXAMPLE.COM
        Krb5Keytab /etc/httpd/conf/http.<hostname>.keytab
        KrbSaveCredentials off
        Require valid-user
    </Location>
    """
    # Web UI Needed
    can_login = False
    can_register = False
    can_logout = False

    def configure_user(self, user):
        """
        Configures a user after creation and returns the updated user.

        By default, returns the user unmodified.
        """
        user.email = user.username + '@' + settings.KRB5_REALM.lower()
        user.set_unusable_password()
        user.save()
        return user

    def clean_username(self, username):
        """
        Performs any cleaning on the "username" prior to using it to get or
        create the user object.  Returns the cleaned username.

        For more info, reference clean_username function in
        django/auth/backends.py
        """
        return username.replace('@' + settings.KRB5_REALM, '')
