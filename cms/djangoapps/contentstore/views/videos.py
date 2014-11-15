"""
Views related to the video upload feature
"""

from boto import s3
from pytz import UTC
from uuid import uuid4
from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_http_methods

from opaque_keys.edx.keys import CourseKey
from edxval.api import create_video

from xmodule.modulestore.django import modulestore
from xmodule.assetstore import AssetMetadata
from util.json_request import expect_json, JsonResponse

from contentstore.utils import reverse_course_url
from .course import get_course_and_check_access


__all__ = ['videos_handler', 'videos_detail_handler']


# String constant used in asset keys to identify video assets.
VIDEO_ASSET_TYPE = 'video'

# Default expiration, in seconds, of one-time URLs used for uploading videos.
KEY_EXPIRATION_IN_SECONDS = 3600


class UploadStatus(object):
    """
    Constant values for the various statuses of video uploads
    """
    uploading = _("Uploading")
    valid_file = _("File Valid")
    invalid_file = _("File Invalid")
    in_progress = _("In Progress")
    complete = _("Complete")


@expect_json
@login_required
@require_http_methods(("GET", "POST", "PATCH"))
def videos_handler(request, course_key_string):
    """
    The restful handler for video uploads.

    GET
        json: return json representing the videos that have been uploaded and their statuses
    PATCH or POST
        json: upload a set of videos
    """
    # The feature flag should be enabled
    assert settings.FEATURES['ENABLE_VIDEO_UPLOAD_PIPELINE']

    course_key = CourseKey.from_string(course_key_string)

    # For now, assume all studio users that have access to the course can upload videos.
    # In the future, we plan to add a new org-level role for video uploaders.
    course = get_course_and_check_access(course_key, request.user)

    # Check whether the video upload feature is configured for this course
    if not course.video_pipeline_configured:
        return JsonResponse({"error": _("Course not configured properly for video upload.")}, status=404)

    if 'application/json' in request.META.get('HTTP_ACCEPT', 'application/json'):
        if request.method == 'GET':
            return videos_index_json(course)
        else:
            return videos_post(course, request)

    return HttpResponse(status=406)


@expect_json
@login_required
@require_http_methods(("POST"))
def videos_detail_handler(request, course_key_string, edx_video_id):
    """
    JSON API endpoint for manipulating a video via its edx_video_id.

    POST
        json: update video based on provided information
    """
    course_key = CourseKey.from_string(course_key_string)
    course = get_course_and_check_access(course_key, request.user)
    return HttpResponse(status=406)


def videos_index_json(course):
    """
    Returns a JSON in the following format: {
        videos: [
           {
              edx_video_id: xxx,
              file_name: xxx,
              date_uploaded: xxx,
              status: xxx,
           },
           ...
        ]
    }
    """
    videos = []
    for metadata in modulestore().get_all_asset_metadata(course.id, VIDEO_ASSET_TYPE):
        videos.append({
            'edx_video_id': metadata.asset_id.path,
            'file_name': metadata.fields['file_name'],
            # TODO PLAT-278 use created_on field instead  # pylint: disable=fixme
            'date_uploaded': metadata.fields['upload_timestamp'],
            'status': metadata.fields['status'],
        })
    return JsonResponse({'videos': videos}, status=200)


def videos_post(course, request):
    """
    Input (JSON): {
        files: [
            { file_name: xxx },
            ...
        ]
    }
    Returns (JSON): {
        files: [
            { file_name: xxx, upload_url: xxx },
            ...
        ]
    }
    """
    bucket = storage_service_bucket()
    course_video_upload_token = course.video_upload_pipeline['course_video_upload_token']

    video_files = request.json['files']
    for video_file in video_files:
        file_name = video_file['file_name']

        # 1. generate edx_video_id
        edx_video_id = generate_edx_video_id()

        # 2. generate key for uploading file
        key = storage_service_key(
            bucket,
            folder_name=settings.VIDEO_UPLOAD_PIPELINE['FOLDER'],
            file_name=edx_video_id,
        )

        # 3. set meta data for the file
        video_handler_url = reverse_course_url(
            'videos_detail_handler',
            course.id,
            kwargs={'edx_video_id': edx_video_id}
        )
        for metadata_name, value in [
            ('course_video_upload_token', course_video_upload_token),
            ('user_supplied_file_name', file_name),
            ('video_handler_url', video_handler_url)

        ]:
            key.set_metadata(metadata_name, value)

        # 4. generate URL
        video_file['upload-url'] = key.generate_url(KEY_EXPIRATION_IN_SECONDS, 'PUT')

        # 5. persist edx_video_id Status
        video_meta_data = AssetMetadata(
            course.id.make_asset_key(VIDEO_ASSET_TYPE, edx_video_id),
            fields={
                'file_name': file_name,
                'upload_timestamp': datetime.now(UTC),
                'status': UploadStatus.uploading
            }
        )
        modulestore().save_asset_metadata(video_meta_data, request.user.id)

        # 6. persist edx_video_id in VAL
        create_video({
            'edx_video_id': edx_video_id,
            'client_video_id': file_name,
            'encoded_videos': [],
        })

    return JsonResponse({'files': video_files}, status=200)


def generate_edx_video_id():
    """
    Generates and returns an edx-video-id to uniquely identify a new logical video.
    """
    return "edx-vid-v1:{}".format(uuid4())


def storage_service_bucket():
    """
    Returns a bucket in a cloud-based storage service for video uploads.
    """
    conn = s3.connection.S3Connection(
        settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY
    )
    return conn.get_bucket(settings.VIDEO_UPLOAD_PIPELINE['BUCKET'])


def storage_service_key(bucket, folder_name, file_name):
    """
    Returns a key to the given file in the given folder in the given bucket for video uploads.
    """
    key_name = "{}/{}/{}".format(
        settings.VIDEO_UPLOAD_PIPELINE['ROOT_PATH'],
        folder_name,
        file_name
    )
    return s3.key.Key(bucket, key_name)
