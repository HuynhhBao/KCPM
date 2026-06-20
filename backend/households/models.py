import uuid
import secrets

from django.conf import settings
from django.db import models

from core.models import BaseModel


def generate_invite_code():
    return secrets.token_hex(4).upper()


class Household(BaseModel):
    name = models.CharField(max_length=255)

    description = models.TextField(
        blank=True
    )

    avatar = models.ImageField(
        upload_to='households/',
        blank=True,
        null=True
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_households'
    )

    invite_code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True
    )

    is_active = models.BooleanField(
        default=True
    )

    def save(self, *args, **kwargs):
        if not self.invite_code:
            code = generate_invite_code()

            while Household.objects.filter(
                invite_code=code
            ).exists():
                code = generate_invite_code()

            self.invite_code = code

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class HouseholdMember(BaseModel):
    class Role(models.TextChoices):
        OWNER = 'owner', 'Chủ nhóm'
        MEMBER = 'member', 'Thành viên'

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name='members'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='household_memberships'
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER
    )

    joined_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        unique_together = (
            'household',
            'user'
        )

    def __str__(self):
        return (
            f'{self.user.email} - '
            f'{self.household.name}'
        )


class Activity(BaseModel):
    class ActivityType(models.TextChoices):
        EXPENSE_CREATED = (
            'expense_created',
            'Thêm khoản chi',
        )
        EXPENSE_UPDATED = (
            'expense_updated',
            'Sửa khoản chi',
        )
        EXPENSE_DELETED = (
            'expense_deleted',
            'Xóa khoản chi',
        )
        MEMBER_JOINED = (
            'member_joined',
            'Thành viên tham gia',
        )
        MEMBER_LEFT = (
            'member_left',
            'Thành viên rời nhóm',
        )
        MEMBER_KICKED = (
            'member_kicked',
            'Xóa thành viên khỏi nhóm',
        )
        VIRTUAL_MEMBER_CREATED = (
            'virtual_member_created',
            'Tạo thành viên ảo',
        )
        HOUSEHOLD_DELETED = (
            'household_deleted',
            'Xóa nhóm',
        )

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name='activities'
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activities'
    )

    activity_type = models.CharField(
        max_length=50,
        choices=ActivityType.choices
    )

    title = models.CharField(
        max_length=255
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True
    )

    metadata = models.JSONField(
        default=dict,
        blank=True
    )

    def __str__(self):
        return self.title