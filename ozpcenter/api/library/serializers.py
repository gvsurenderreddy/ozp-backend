"""
Serializers
"""
import logging

from rest_framework import serializers

from ozpcenter import models
from ozpcenter.api.library import model_access
import ozpcenter.api.listing.model_access as listing_model_access
import ozpcenter.api.image.serializers as image_serializers

# Get an instance of a logger
logger = logging.getLogger('ozp-center.' + str(__name__))


class LibrarySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.ApplicationLibraryEntry


class LibraryListingSerializer(serializers.HyperlinkedModelSerializer):
    small_icon = image_serializers.ImageSerializer(required=False)
    large_icon = image_serializers.ImageSerializer(required=False)
    banner_icon = image_serializers.ImageSerializer(required=False)

    class Meta:
        model = models.Listing
        fields = ('id', 'title', 'unique_name', 'launch_url', 'small_icon',
            'large_icon', 'banner_icon')
        read_only_fields = ('title', 'unique_name', 'launch_url', 'small_icon',
            'large_icon', 'banner_icon')
        # Any AutoFields on your model (which is what the automatically
        # generated id key is) are set to read-only by default when Django
        # REST Framework is creating fields in the background. read-only fields
        # will not be part of validated_data. Override that behavior using the
        # extra_kwargs
        extra_kwargs = {
            "id": {
                "read_only": False,
                "required": False,
            },
        }


class UserLibrarySerializer(serializers.ModelSerializer):
    """
    Serializer for self/library - owner is always current user
    """
    listing = LibraryListingSerializer()

    class Meta:
        model = models.ApplicationLibraryEntry
        fields = ('listing', 'folder', 'id')

    def validate(self, data):
        """
        Check for listing id (folder is optional)
        """
        if 'listing' not in data:
            raise serializers.ValidationError('No listing provided')

        username = self.context['request'].user.username
        listing = listing_model_access.get_listing_by_id(username,
            data['listing']['id'])

        if listing:
            if not listing.is_enabled:
                raise serializers.ValidationError('Can not bookmark apps that are disabled')
        else:
            raise serializers.ValidationError('Listing id entry not found')

        if 'id' not in data['listing']:
            raise serializers.ValidationError('No listing id provided')
        if 'folder' in data:
            if not data.get('folder'):
                data['folder'] = None

        return data

    def create(self, validated_data):
        username = self.context['request'].user.username
        listing_id = validated_data['listing']['id']
        folder_name = validated_data.get('folder')
        return model_access.create_self_user_library_entry(username, listing_id, folder_name)
