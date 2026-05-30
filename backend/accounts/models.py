from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)

    full_name = models.CharField(
        max_length=255,
        blank=True,
        default=''
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True
    )

    avatar_data = models.BinaryField(
        blank=True,
        null=True
    )

    avatar_content_type = models.CharField(
        max_length=100,
        blank=True,
        default=''
    )

    avatar_file_name = models.CharField(
        max_length=255,
        blank=True,
        default=''
    )

    avatar_updated_at = models.DateTimeField(
        blank=True,
        null=True
    )

    bank_name = models.CharField(
        max_length=100,
        blank=True,
        default=''
    )

    bank_account_number = models.CharField(
        max_length=50,
        blank=True,
        default=''
    )

    bank_account_holder = models.CharField(
        max_length=255,
        blank=True,
        default=''
    )

    auth_provider = models.CharField(
        max_length=20,
        default='email'
    )

    email_verified = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'

    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email