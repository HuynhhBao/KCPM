from django.contrib.auth import get_user_model
from accounts.avatar_utils import build_user_avatar_url
from accounts.cloudinary_storage import (
    delete_cloudinary_avatar_safely,
    upload_user_avatar,
)
from rest_framework import serializers
import mimetypes
import re

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'full_name',
            'phone_number',
            'password',
        ]

    def validate_email(self, value):
        email = value.lower().strip()

        existing_user = User.objects.filter(
            email=email
        ).first()

        if (
            existing_user and
            existing_user.email_verified
        ):
            raise serializers.ValidationError(
                'Email đã tồn tại'
            )

        return email

    def create(self, validated_data):
        password = validated_data.pop('password')

        user = User(
            **validated_data,
            is_active=False,
            email_verified=False,
        )

        user.set_password(password)
        user.save()

        return user


class VerifyRegisterOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    otp = serializers.CharField(
        min_length=6,
        max_length=6
    )


class ResendRegisterOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()


class UserProfileSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(
        write_only=True,
        required=False,
        allow_null=True
    )

    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'full_name',
            'phone_number',
            'avatar',
            'avatar_url',
            'bank_name',
            'bank_account_number',
            'bank_account_holder',
            'auth_provider',
            'email_verified',
        ]

        read_only_fields = [
            'id',
            'email',
            'username',
            'avatar_url',
            'auth_provider',
            'email_verified',
        ]

    def get_avatar_url(self, obj):
        request = self.context.get('request')

        return build_user_avatar_url(
            obj,
            request,
        )

    def validate_full_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                'Họ và tên không được để trống'
            )

        if len(value) < 2:
            raise serializers.ValidationError(
                'Họ và tên tối thiểu 2 ký tự'
            )

        return value

    def validate_phone_number(self, value):
        if value is None:
            return ''

        value = value.strip()

        if not value:
            return ''

        if not re.match(r'^\+?[0-9]{9,15}$', value):
            raise serializers.ValidationError(
                'Số điện thoại không hợp lệ'
            )

        return value

    def validate_bank_name(self, value):
        if value is None:
            return ''

        return value.strip()

    def validate_bank_account_number(self, value):
        if value is None:
            return ''

        value = value.strip()

        if not value:
            return ''

        if not re.match(r'^[0-9]{4,30}$', value):
            raise serializers.ValidationError(
                'Số tài khoản chỉ được chứa chữ số, từ 4 đến 30 ký tự'
            )

        return value

    def validate_bank_account_holder(self, value):
        if value is None:
            return ''

        return value.strip().upper()

    def validate_avatar(self, value):
        if not value:
            return value

        max_size = 2 * 1024 * 1024

        if value.size > max_size:
            raise serializers.ValidationError(
                'Ảnh đại diện tối đa 2MB'
            )

        allowed_types = [
            'image/jpeg',
            'image/png',
            'image/webp',
        ]

        content_type = getattr(value, 'content_type', '') or ''

        if (
            not content_type or
            content_type == 'application/octet-stream'
        ):
            guessed_type, _ = mimetypes.guess_type(
                getattr(value, 'name', '')
            )

            if guessed_type:
                content_type = guessed_type

        if content_type and content_type not in allowed_types:
            raise serializers.ValidationError(
                'Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP'
            )

        return value
    
    def update(self, instance, validated_data):
        avatar_file = validated_data.pop(
            'avatar',
            None
        )

        for attr, value in validated_data.items():
            setattr(
                instance,
                attr,
                value,
            )

        old_storage_path = (
            instance.avatar_storage_path or ''
        )

        if avatar_file:
            upload_result = upload_user_avatar(
                user=instance,
                uploaded_file=avatar_file,
            )

            instance.avatar_url = upload_result[
                'avatar_url'
            ]

            instance.avatar_storage_path = upload_result[
                'avatar_storage_path'
            ]

            instance.avatar_updated_at = upload_result[
                'avatar_updated_at'
            ]

            instance.avatar_data = None
            instance.avatar_content_type = ''
            instance.avatar_file_name = ''

            try:
                if instance.avatar:
                    instance.avatar.delete(
                        save=False,
                    )
            except Exception:
                pass

            try:
                instance.avatar = None
            except Exception:
                pass

        instance.save()

        if (
            avatar_file and
            old_storage_path and
            old_storage_path != instance.avatar_storage_path
        ):
            delete_cloudinary_avatar_safely(
                old_storage_path,
            )

        return instance

    def validate(self, attrs):
        bank_name = attrs.get(
            'bank_name',
            getattr(self.instance, 'bank_name', ''),
        )

        bank_account_number = attrs.get(
            'bank_account_number',
            getattr(self.instance, 'bank_account_number', ''),
        )

        bank_account_holder = attrs.get(
            'bank_account_holder',
            getattr(self.instance, 'bank_account_holder', ''),
        )

        bank_values = [
            bank_name.strip() if bank_name else '',
            bank_account_number.strip() if bank_account_number else '',
            bank_account_holder.strip() if bank_account_holder else '',
        ]

        has_any_bank_info = any(bank_values)
        has_all_bank_info = all(bank_values)

        if has_any_bank_info and not has_all_bank_info:
            raise serializers.ValidationError(
                {
                    'bank_account_number':
                    'Vui lòng nhập đầy đủ tên ngân hàng, số tài khoản và chủ tài khoản'
                }
            )

        return attrs

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True
    )

    new_password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    confirm_password = serializers.CharField(
        write_only=True
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {
                    'confirm_password':
                    'Mật khẩu xác nhận không khớp'
                }
            )

        return attrs


class ForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    otp = serializers.CharField(
        min_length=6,
        max_length=6
    )

    new_password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    confirm_password = serializers.CharField(
        write_only=True
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {
                    'confirm_password':
                    'Mật khẩu xác nhận không khớp'
                }
            )

        return attrs