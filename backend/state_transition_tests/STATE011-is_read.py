import os
import sys
from pathlib import Path
from types import SimpleNamespace

import django
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.contrib.auth import get_user_model
from rest_framework import status

from notifications.models import Notification
from notifications.views import NotificationMarkAllReadView, NotificationMarkReadView


pytestmark = pytest.mark.django_db


def create_user(email, full_name="Test User"):
    User = get_user_model()
    username = email.split("@")[0]

    return User.objects.create_user(
        username=username,
        email=email,
        password="StrongPass123",
        full_name=full_name,
    )


def create_notification(recipient, actor, is_read=False, title="Test notification"):
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=Notification.NotificationType.DEBT_CREATED,
        level=Notification.Level.IN_APP,
        title=title,
        is_read=is_read,
    )


class TestNotificationMarkReadView:
    def test_patch_marks_single_notification_as_read_by_id(self):
        user = create_user("reader@example.com", "Reader")
        actor = create_user("actor@example.com", "Actor")
        notification = create_notification(
            recipient=user,
            actor=actor,
            is_read=False,
        )

        response = NotificationMarkReadView().patch(
            SimpleNamespace(user=user),
            pk=notification.id,
        )

        notification.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert notification.is_read is True


class TestNotificationMarkAllReadView:
    def test_patch_bulk_marks_all_current_user_unread_notifications_as_read(self):
        user = create_user("bulk-reader@example.com", "Bulk Reader")
        actor = create_user("bulk-actor@example.com", "Bulk Actor")
        other_user = create_user("other-reader@example.com", "Other Reader")

        unread_notification = create_notification(
            recipient=user,
            actor=actor,
            is_read=False,
            title="Unread notification",
        )
        already_read_notification = create_notification(
            recipient=user,
            actor=actor,
            is_read=True,
            title="Already read notification",
        )
        other_user_notification = create_notification(
            recipient=other_user,
            actor=actor,
            is_read=False,
            title="Other user notification",
        )

        response = NotificationMarkAllReadView().patch(SimpleNamespace(user=user))

        unread_notification.refresh_from_db()
        already_read_notification.refresh_from_db()
        other_user_notification.refresh_from_db()

        assert response.status_code == status.HTTP_200_OK
        assert unread_notification.is_read is True
        assert already_read_notification.is_read is True
        assert other_user_notification.is_read is False
        assert Notification.objects.filter(recipient=user, is_read=False).count() == 0