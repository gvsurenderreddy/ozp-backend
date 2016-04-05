"""
PKI Authentication

nginx ssl_module vars in headers:
$ssl_client_s_dn -> HTTP_X_SSL_USER_DN
$ssl_client_i_dn -> HTTP_X_SSL_ISSUER_DN
$ssl_client_verify -> HTTP_X_SSL_AUTHENTICATED
"""
import logging

from django.conf import settings

from rest_framework import authentication
from rest_framework import exceptions

import ozpcenter.models as models
import ozpcenter.utils as utils

try:
    from django.contrib.auth import get_user_model

    User = get_user_model()
except ImportError:
    from django.contrib.auth.models import User

logger = logging.getLogger('ozp-center')


class PkiAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        # ensure we're using HTTPS
        if not request.is_secure():
            logger.error('Insecure request (not HTTPS): incompatible with PkiAuthentication')
            return None

        # get status of client authentication
        authentication_status = request.META.get('HTTP_X_SSL_AUTHENTICATED', None)
        if not authentication_status:
            logger.error('Missing header: HTTP_X_SSL_AUTHENTICATED')
            return None

        # this assumes that we're using nginx and that the value of
        # $ssl_client_verify was put into the HTTP_X_SSL_AUTHENTICATED header
        if authentication_status != 'SUCCESS':
            logger.error('Value of HTTP_X_SSL_AUTHENTICATED header not SUCCESS, got %s instead' % authentication_status)
            return None

        # get the user's DN
        dn = request.META.get('HTTP_X_SSL_USER_DN', None)

        # get the issuer DN:
        issuer_dn = request.META.get('HTTP_X_SSL_ISSUER_DN', None)
        # TODO: do we need to preprocess/sanitize this in any way?
        if not dn:
            logger.error('HTTP_X_SSL_USER_DN missing from header')
            return None
        if not issuer_dn:
            logger.error('HTTP_X_SSL_ISSUER_DN missing from header')
            return None

        # using test certs generated by openssl, a '/' is used as a separator,
        # which is not url friendly and causes our demo authorization service
        # to choke. Replace these with commas instead
        if settings.OZP['PREPROCESS_DN']:
            dn = _preprocess_dn(dn)
            issuer_dn = _preprocess_dn(issuer_dn)

        logger.info('Attempting to authenticate user with dn: %s and issuer dn: %s' % (dn, issuer_dn))

        profile = _get_profile_by_dn(dn, issuer_dn)

        if profile:
            logger.info('found user %s, authentication succeeded' % profile.user.username)
            return (profile.user, None)
        else:
            logger.error('Failed to find/create user for dn %s. Authentication failed' % dn)
            return None


def _preprocess_dn(original_dn):
    """
    Reverse the DN and replace slashes with commas
    """
    # remove leading slash
    dn = original_dn[1:]
    dn = dn.split('/')
    dn = dn[::-1]
    dn = ", ".join(dn)
    return dn


def _get_profile_by_dn(dn, issuer_dn='default issuer dn'):
    """
    Returns a user profile for a given DN

    If a profile isn't found with the given DN, create one
    """
    # look up the user with this dn. if the user doesn't exist, create them
    profile = models.Profile.objects.filter(dn__iexact=dn).first()
    if profile:
        if not profile.user.is_active:
            logger.warning('User %s tried to login but is inactive' % dn)
            return None
        # update the issuer_dn
        if profile.issuer_dn != issuer_dn:
            logger.info('updating issuer dn for user %s' % profile.user.username)
            profile.issuer_dn = issuer_dn
            profile.save()
        return profile
    else:
        logger.info('creating new user for dn: %s' % dn)
        if 'CN=' in dn:
            cn = utils.find_between(dn, 'CN=', ',')
        else:
            cn = dn

        kwargs = {'display_name': cn, 'dn': dn, 'issuer_dn': issuer_dn}
        # sanitize username
        username = cn[0:30]
        username = username.replace(' ', '_')  # no spaces
        username = username.replace("'", "")  # no apostrophes
        username = username.lower()  # all lowercase
        # make sure this username doesn't exist
        count = User.objects.filter(username=username).count()
        if count != 0:
            new_username = username[0:27]
            count = User.objects.filter(username__startswith=new_username).count()
            new_username = '%s_%s' % (new_username, count + 1)
            username = new_username

        # now check again - if this username exists, we have a problem
        count = User.objects.filter(
            username=username).count()
        if count != 0:
            logger.error('Cannot create new user for dn %s, username %s already exists' % (dn, username))
            return None

        profile = models.Profile.create_user(username, **kwargs)
        logger.info('created new profile for user %s' % profile.user.username)
        return profile
