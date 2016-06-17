"""
Serializers
"""
import logging

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from ozpcenter import models
import ozpcenter.api.listing.model_access as listing_model_access
import ozpcenter.api.agency.model_access as agency_model_access
import ozpcenter.api.notification.model_access as model_access

# Get an instance of a logger
logger = logging.getLogger('ozp-center.' + str(__name__))


class ShortUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('username',)


class ShortProfileSerializer(serializers.ModelSerializer):
    user = ShortUserSerializer()

    class Meta:
        model = models.Profile
        fields = ('user',)


class NotificationListingSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Listing
        fields = ('id', 'title')

        extra_kwargs = {
            'title': {'validators': []}
        }


class NotificationAgencySerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Agency
        fields = ('id', 'title')

        extra_kwargs = {
            'title': {'validators': []}
        }


class GenericField(serializers.ReadOnlyField):
    """
    Read Only Field
    """

    def to_native(self, obj):
        return obj


class NotificationSerializer(serializers.ModelSerializer):
    author = ShortProfileSerializer(required=False)
    peer = ShortProfileSerializer(required=False)
    listing = NotificationListingSerializer(required=False)
    agency = NotificationAgencySerializer(required=False)
    notification_type = GenericField(required=False)

    extra_kwargs = {
        'listing': {'validators': []},
        'agency': {'validators': []},
        'peer': {'validators': []},
    }

    class Meta:
        model = models.Notification
        fields = ('id',
                  'created_date',
                  'expires_date',
                  'message',
                  'author',
                  'listing',
                  'agency',
                  'peer',
                  'notification_type')

    def validate(self, validated_data):
        """ Responsible of cleaning and validating user input data """
        initial_data = self.initial_data
        username = self.context['request'].user.username

        if 'message' not in validated_data and self.context['request'].method == 'POST':
            raise serializers.ValidationError('Messsage field is required for POST Request')

        if 'listing' in initial_data and 'agency' in initial_data:
            raise serializers.ValidationError('Notification can only be listing or agency')

        # TODO: Figure how to get listing data using validated data
        listing = initial_data.get('listing')
        if listing and listing.get('id'):
            try:
                validated_data['listing'] = listing_model_access.get_listing_by_id(
                    username, initial_data['listing']['id'], True)
            except ObjectDoesNotExist:
                raise serializers.ValidationError('Valid Listing ID is required, Could not find listing')
        else:
            validated_data['listing'] = None

        agency = initial_data.get('agency')
        if agency and agency.get('id'):
            try:
                validated_data['agency'] = agency_model_access.get_agency_by_id(
                    initial_data['agency']['id'], True)
            except ObjectDoesNotExist:
                raise serializers.ValidationError('Valid agency ID is required, Could not find listing')
        else:
            validated_data['agency'] = None

        return validated_data

    def create(self, validated_data):
        """
        Used to create notifications
        """
        username = self.context['request'].user.username
        notification = model_access.create_notification(username,
                                                        validated_data['expires_date'],
                                                        validated_data['message'],
                                                        validated_data['listing'],
                                                        validated_data['agency'])
        return notification

    def update(self, instance, validated_data):
        """
        This is only used to update the expired_date field (effectively
        deleting a notification while still leaving a record of it)
        """
        username = self.context['request'].user.username
        notification = model_access.update_notification(username,
                                                        instance,
                                                        validated_data['expires_date'])
        return notification
