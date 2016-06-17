"""
Library Views

Requirements
============
* The user shall be able to

GET /api/self/library
Summary:
    Return The id and unique name of each listing in the user's library

POST /api/self/library/import_bookmarks/{bookmark_notification_id}
Summary:
    Return The id and unique name of each listing in the user's library
"""
import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import list_route
from rest_framework.response import Response

from ozpcenter import permissions
from ozpcenter.api.library import serializers
from ozpcenter.api.library import model_access


# Get an instance of a logger
logger = logging.getLogger('ozp-center.' + str(__name__))


class LibraryViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet for getting all library entries for all users

    Access Control
    ===============
    Must be an Org Steward to access this endpoint

    URIs
    ======
    GET /api/library
    Summary:
        Get a list of all user's Application Library Entries

    Response:
        200 - Successful operation - [LibrarySerializer]

    GET /api/library/{pk}
    Summary:
        Find an Application Library Entry by ID

    DELETE /api/library/{pk}
    Summary:
        Delete an Application Library Entry by ID

    POST, PUT, PATCH, DELETE api/library/<id> - unallowed (for now)
    """
    permission_classes = (permissions.IsOrgSteward,)
    queryset = model_access.get_all_library_entries()
    serializer_class = serializers.LibrarySerializer


class UserLibraryViewSet(viewsets.ViewSet):
    """
    Listings that have been bookmarked by the current user

    Access Control
    ===============
    User - only for current request user

    URI
    ======
    /api/self/library
    """
    permission_classes = (permissions.IsUser,)

    def get_queryset(self):
        listing_type = self.request.query_params.get('type', None)
        queryset = model_access.get_self_application_library(self.request.user.username, listing_type)
        return queryset

    def create(self, request):
        """
        Bookmark a Listing for the current user.

        POST JSON data:
        {
            "listing":
                {
                    "id": 1
                },
            "folder": "folderName" (optonal)
        }
        ---
        parameters:
            - name: body
              required: true
              paramType: body
        parameters_strategy:
            form: replace
            query: replace
        omit_serializer: true
        """
        serializer = serializers.UserLibrarySerializer(data=request.data,
            context={'request': request})
        if not serializer.is_valid():
            logger.error('{0!s}'.format(serializer.errors))
            return Response(serializer.errors,
                status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request):
        """
        The current user's bookmarked listings
        ---
        serializer: ozpcenter.api.library.serializers.UserLibrarySerializer
        """
        queryset = self.get_queryset()
        serializer = serializers.UserLibrarySerializer(queryset,
            many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        Retrieve by library id (not listing id)
        """
        queryset = self.get_queryset()
        library_entry = get_object_or_404(queryset, pk=pk)
        serializer = serializers.UserLibrarySerializer(library_entry,
            context={'request': request})
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        """
        Remove a Listing from the current user's library (unbookmark)

        Delete by library id, not listing id
        """
        queryset = self.get_queryset()
        library_entry = get_object_or_404(queryset, pk=pk)
        library_entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @list_route(methods=['put'], permission_classes=[permissions.IsUser])
    def update_all(self, request):
        """
        Update ALL of the user's library entries

        Used to move library entries into different folders for HUD

        Notes:
            This method is different than most. The ViewSet update method only
            works on a single instance, hence the use of a special update_all
            method. Serializers must be customized to support nested writable
            representations, and even after doing so, the input data validation
            didn't seem acceptable. Hence this customized method

        [
            {
                "listing": {
                    "id": 1
                },
                "folder": "folderName" (or null),
                "id": 2
            },
            {
                "listing": {
                    "id": 2
                },
                "folder": "folderName" (or null),
                "id": 1
            }
        ]
        ---
        parameters:
            - name: body
              required: true
              paramType: body
        parameters_strategy:
            form: replace
            query: replace
        omit_serializer: true
        """
        username = request.user.username
        errors, data = model_access.batch_update_user_library_entry(username, request.data)
        if errors:
            return Response({'message': '{0}'.format(errors)}, status=status.HTTP_500_BAD_REQUEST)
        else:
            return Response(data, status=status.HTTP_200_OK)
