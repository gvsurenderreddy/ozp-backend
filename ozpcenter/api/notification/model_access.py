"""
Model access
"""
import datetime
import logging
import pytz
from enum import Enum

from ozpcenter import errors
from ozpcenter import models
import ozpcenter.model_access as generic_model_access


# Get an instance of a logger
logger = logging.getLogger('ozp-center.' + str(__name__))


class UserRoleType(Enum):
    APPS_MALL_STEWARD = 'APPS_MALL_STEWARD'
    ORG_STEWARD = 'ORG_STEWARD'
    USER = 'USER'


class NotificationActionEnum(Enum):
    CREATE = 'Create'
    UPDATE = 'Update'
    DELETE = 'Delete'


class NotificationTypeEnum(Enum):
    SYSTEM = 'System-Wide Notification'
    AGENCY = 'Agency-Wide Notification'
    LISTING = 'Listing-Specific Notification'


def org_create_listing_condition(profile_obj, listing):
    if profile_obj not in listing.owners.all():
        raise errors.PermissionDenied(
            'Cannot create a notification for a listing you do not own')
    return True


def user_create_listing_condition(profile_obj, listing):
    """
    Listing create condition for user

    Args:
        profile_obj (models.Profile): Profile
        listing (models.Listing): Listing

    Return:
        bool: if user can create listings
    """
    if profile_obj not in listing.owners.all():
        raise errors.PermissionDenied(
            'Cannot create a notification for a listing you do not own')
    return True


def raise_(exception):
    """
    Helper Function to raise exceptions

    Arg:
        exception (Exception): Exception class
    """
    raise exception


def _check_profile_permission(user_role_type, notification_action, notification_type, **kwargs):
    """
    Check Permission

    Permissions:
        APP_MALL_STEWARD
            can [CREATE, UPDATE, DISMISS, DELETE]
            notification type [SYSTEM, AGENCY, LISTING]

        ORG_STEWARD
            can [CREATE, UPDATE, DISMISS]
            notification type [AGENCY(org_steward_agency_condition), LISTING(c2)]
        USER
            can [CREATE, DISMISS]
            notification type [LISTING(c3)]

    Return:
        lambda function
    """
    profile_obj = kwargs.get('profile_obj')
    listing = kwargs.get('listing')

    permissions = {
        UserRoleType.APPS_MALL_STEWARD: {
            NotificationActionEnum.CREATE: {
                NotificationTypeEnum.SYSTEM: lambda: True,
                NotificationTypeEnum.AGENCY: lambda: True,
                NotificationTypeEnum.LISTING: lambda: True
            },
            NotificationActionEnum.UPDATE: {
                NotificationTypeEnum.SYSTEM: lambda: True,
                NotificationTypeEnum.AGENCY: lambda: True,
                NotificationTypeEnum.LISTING: lambda: True
            },
            NotificationActionEnum.DELETE: {
                NotificationTypeEnum.SYSTEM: lambda: True,
                NotificationTypeEnum.AGENCY: lambda: True,
                NotificationTypeEnum.LISTING: lambda: True
            }
        },
        UserRoleType.ORG_STEWARD: {
            NotificationActionEnum.CREATE: {
                NotificationTypeEnum.SYSTEM: lambda: raise_(errors.PermissionDenied('Only app mall stewards can create system notifications')),
                NotificationTypeEnum.AGENCY: lambda: True,
                NotificationTypeEnum.LISTING: lambda: True  # TODO: org_create_listing_condition(profile_obj, listing)
            },
            NotificationActionEnum.UPDATE: {
                # lambda: raise_(errors.PermissionDenied('Only app mall
                # stewards can update system notifications')),
                NotificationTypeEnum.SYSTEM: lambda: True,
                NotificationTypeEnum.AGENCY: lambda: True,
                NotificationTypeEnum.LISTING: lambda: True
            },
            NotificationActionEnum.DELETE: {
                # lambda: raise_(errors.PermissionDenied('Only app mall
                # stewards can delete system notifications')),
                NotificationTypeEnum.SYSTEM: lambda: True,
                NotificationTypeEnum.AGENCY: lambda: True,
                NotificationTypeEnum.LISTING: lambda: True
            }
        },
        UserRoleType.USER: {
            NotificationActionEnum.CREATE: {
                NotificationTypeEnum.SYSTEM: lambda: raise_(errors.PermissionDenied('Only app mall stewards can create system notifications')),
                NotificationTypeEnum.AGENCY: lambda: raise_(errors.PermissionDenied('Only org stewards can create agency notifications')),
                NotificationTypeEnum.LISTING: lambda: user_create_listing_condition(profile_obj, listing)
            },
            NotificationActionEnum.UPDATE: {
                NotificationTypeEnum.SYSTEM: lambda: raise_(errors.PermissionDenied('Only app mall stewards can update system notifications')),
                NotificationTypeEnum.AGENCY: lambda: raise_(errors.PermissionDenied('Only org stewards can create agency notifications')),
                NotificationTypeEnum.LISTING: None
            },
            NotificationActionEnum.DELETE: {
                NotificationTypeEnum.SYSTEM: lambda: raise_(errors.PermissionDenied('Only app mall stewards can delete system notifications')),
                NotificationTypeEnum.AGENCY: lambda: raise_(errors.PermissionDenied('Only org stewards can create agency notifications')),
                NotificationTypeEnum.LISTING: None
            }
        }
    }
    return permissions.get(user_role_type, {}).get(notification_action, {}).get(notification_type, lambda: raise_(errors.PermissionDenied('Unknown Permissions')))


def create_notification(author_username, expires_date, message, listing=None, agency=None, peer=None):
    """
    Create Notification

    Notifications Types:
        * System-Wide Notification is made up of [expires_date, author_username, message]
        * Agency-Wide Notification is made up of [expires_date, author_username, message, agency]
        * Listing-Specific Notification is made up of [expires_date, author_username, message, listing]

    Args:
        author_username (str): Username of author
        expires_date (datetime.datetime): Expires Date (datetime.datetime(2016, 6, 24, 1, 0, tzinfo=<UTC>))
        message (str): Message of notification
        listing (models.Listing)-Optional: Listing
        Agency (models.Agency)-Optional: Agency

    Return:
        models.Notification: Created Notification

    Raises:
        AssertionError: If author_username or expires_date or message is None
    """
    assert (author_username is not None), 'Author Username is necessary'
    assert (expires_date is not None), 'Expires Date is necessary'
    assert (message is not None), 'Message is necessary'
    assert not(
        listing is not None and agency is not None), 'Notications can not have listing and agency at the same time'

    notification_action = NotificationActionEnum.CREATE
    notification_type = NotificationTypeEnum.SYSTEM

    if listing is not None:
        notification_type = NotificationTypeEnum.LISTING
    elif agency is not None:
        notification_type = NotificationTypeEnum.AGENCY

    user = generic_model_access.get_profile(author_username)
    # TODO: Check if user exist, if not throw Exception Error ?

    user_role_type = UserRoleType(user.highest_role())

    _check_profile_permission(user_role_type,
                              notification_action,
                              notification_type,
                              listing=listing,
                              agency=agency)()

    notification = models.Notification(
        expires_date=expires_date,
        author=user,
        message=message,
        listing=listing,
        agency=agency,
        peer=peer)

    notification.save()
    return notification


def dismiss_notification(notification_instance, username):
    """
    Dismissed a Notification

    Args:
        notification_instance (models.Notification): notification_instance
        username (string)

    Return:
        bool: Notification Dismissed
    """
    user = generic_model_access.get_profile(username)
    notification_instance.dismissed_by.add(user)

    return True


def update_notification(author_username, notification_instance, expires_date):
    """
    Update Notification

    Args:
        notification_instance (models.Notification): notification_instance
        author_username (str): Username of author

    Return:
        models.Notification: Updated Notification
    """
    notification_action = NotificationActionEnum.UPDATE

    notification_type = NotificationTypeEnum.SYSTEM

    if notification_instance.listing is not None:
        notification_type = NotificationTypeEnum.LISTING
    elif notification_instance.agency is not None:
        notification_type = NotificationTypeEnum.AGENCY

    user = generic_model_access.get_profile(author_username)
    # TODO: Check if user exist, if not throw Exception Error ?

    user_role_type = UserRoleType(user.highest_role())

    _check_profile_permission(
        user_role_type, notification_action, notification_type)()

    notification_instance.expires_date = expires_date
    notification_instance.save()
    return notification_instance


def get_self(username):
    """
    Get Profile for username

    Args:
        username (str): current username

    Returns:
        models.Profile if username exist, None if username does not exist
    """
    return generic_model_access.get_profile(username)


def get_all_pending_notifications(for_user=False):
    """
    Gets all system-wide pending notifications

    Includes
     * System Notifications
     * Listing Notifications
     * Agency Notifications

    if for_user:

    Includes
     * System Notifications

    Returns:
        django.db.models.query.QuerySet(models.Notification): List of system-wide pending notifications
    """
    unexpired_system_notifications = models.Notification.objects.filter(
        expires_date__gt=datetime.datetime.now(pytz.utc))

    if for_user:
        unexpired_system_notifications = unexpired_system_notifications.filter(agency__isnull=True,
                                              listing__isnull=True)

    return unexpired_system_notifications


def get_listing_pending_notifications(username):
    """
    Gets all notifications that are regarding a listing in this user's library

    Includes
     * Listing Notifications

    Does not include
     * System Notifications
     * Agency Notifications

    Args:
        username (str): current username to get notifications

    Returns:
        django.db.models.query.QuerySet(models.Notification): List of user's listing pending notifications
    """
    bookmarked_listing_ids = models.ApplicationLibraryEntry.objects \
        .filter(owner__user__username=username) \
        .filter(listing__is_enabled=True) \
        .filter(listing__is_deleted=False) \
        .values_list('listing', flat=True)

    unexpired_listing_notifications = models.Notification.objects.filter(
        expires_date__gt=datetime.datetime.now(pytz.utc),
        listing__pk_in=bookmarked_listing_ids,
        agency__isnull=True)

    return unexpired_listing_notifications


def get_agency_pending_notifications(username):
    """
    Gets all notifications that are regarding a listing in this user's agencies

    Includes
     * Agency Notifications

    Does not include
     * System Notifications
     * Listing Notifications

    Args:
        username (str): current username to get notifications

    Returns:
        django.db.models.query.QuerySet(models.Notification): List of user's agencies pending notifications
    """
    user_agency = generic_model_access.get_profile(
        username).organizations.all()

    unexpired_agency_notifications = models.Notification.objects.filter(
        expires_date__gt=datetime.datetime.now(pytz.utc),
        agency__pk_in=user_agency,
        listing__isnull=True)

    return unexpired_agency_notifications


def get_all_expired_notifications():
    """
    Get all expired notifications

    Includes
    * Listing Notifications
    * Agency Notifications
    * System Notifications

    Returns:
        django.db.models.query.QuerySet(models.Notification): List of system-wide pending notifications
    """
    expired_system_notifications = models.Notification.objects.filter(
        expires_date__lt=datetime.datetime.now(pytz.utc))
    return expired_system_notifications


def get_all_notifications():
    """
    Get all notifications

    Includes
    * Listing Notifications
    * Agency Notifications
    * System Notifications

    Returns:
        django.db.models.query.QuerySet(models.Notification): List of all notifications
    """
    return models.Notification.objects.all()


def get_dismissed_notifications(username):
    """
    Get all dismissed notifications for a user

    Args:
        username (str): current username to get dismissed notifications

    Returns:
        django.db.models.query.QuerySet(models.Notification): List of dismissed notifications
    """
    return models.Notification.objects.filter(dismissed_by__user__username=username)


def get_self_notifications(username):
    """
    Get notifications for current user

    User's Notifications are
        * Notifications that have not yet expired (A)
        * Notifications have not been dismissed by this user (B)
        * Notifications that are regarding a listing in this user's library
          if the notification is listing-specific
        * Notification that are System-wide are included

    Args:
        username (str): current username to get notifications

    Returns:
        django.db.models.query.QuerySet(models.Notification): List of notifications for username
    """
    # Get all notifications that have been dismissed by this user
    dismissed_notifications = get_dismissed_notifications(username)

    # Get all unexpired notifications for listings in this user's library
    unexpired_listing_notifications = get_listing_pending_notifications(
        username)

    # Gets all notifications that are regarding a listing in this user's
    # agencies
    unexpired_agency_notifications = get_agency_pending_notifications(username)

    # Get all unexpired system-wide notifications
    unexpired_system_notifications = get_all_pending_notifications(for_user=True)

    # return (unexpired_system_notifications +
    # unexpired_listing_notifications) - dismissed_notifications
    notifications = (unexpired_system_notifications | unexpired_agency_notifications |
                     unexpired_listing_notifications).exclude(pk__in=dismissed_notifications)

    return notifications
