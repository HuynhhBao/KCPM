from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from notifications.models import FCMDevice

from accounts.serializers import (
    RegisterSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
    ForgotPasswordRequestSerializer,
    ResetPasswordSerializer,
    VerifyRegisterOTPSerializer,
    ResendRegisterOTPSerializer,
)

import logging
import os
import random

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.core.mail import send_mail
from django.contrib.auth import get_user_model

from google.auth.exceptions import GoogleAuthError
from google.oauth2 import id_token
from google.auth.transport import requests

from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework_simplejwt.views import (
    TokenObtainPairView
)

from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer
)

import requests as pyrequests
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse

User = get_user_model()

logger = logging.getLogger(__name__)

OTP_EXPIRE_SECONDS = 600
OTP_RESEND_COOLDOWN = 60
OTP_MAX_ATTEMPTS = 5

FORGOT_PASSWORD_OTP_COOLDOWN = 60

FCM_TOKEN_MAX_LENGTH = 4096

GOOGLE_REQUEST_TIMEOUT = (
    3.05,
    10,
)


class GoogleTokenInvalidError(Exception):
    pass


class GoogleProviderUnavailableError(Exception):
    pass


def consume_cached_otp(
    *,
    otp_key,
    attempts_key,
    submitted_otp,
):
    cached_otp = cache.get(
        otp_key
    )

    if not cached_otp:
        return False

    attempts = cache.get(
        attempts_key,
        0,
    )

    if not isinstance(attempts, int):
        attempts = 0

    if attempts >= OTP_MAX_ATTEMPTS:
        cache.delete(otp_key)
        cache.delete(attempts_key)
        return False

    if cached_otp != submitted_otp:
        attempts += 1

        cache.set(
            attempts_key,
            attempts,
            timeout=OTP_EXPIRE_SECONDS,
        )

        if attempts >= OTP_MAX_ATTEMPTS:
            cache.delete(otp_key)

        return False

    cache.delete(otp_key)
    cache.delete(attempts_key)

    return True


def request_google_json(
    url,
    *,
    params,
):
    try:
        response = pyrequests.get(
            url,
            params=params,
            timeout=GOOGLE_REQUEST_TIMEOUT,
        )

    except (
        pyrequests.Timeout,
        pyrequests.ConnectionError,
    ) as exc:
        raise GoogleProviderUnavailableError(
            'Không thể kết nối dịch vụ Google'
        ) from exc

    if response.status_code in (
        400,
        401,
        403,
    ):
        raise GoogleTokenInvalidError(
            'Google token không hợp lệ'
        )

    try:
        response.raise_for_status()

    except pyrequests.HTTPError as exc:
        raise GoogleProviderUnavailableError(
            'Dịch vụ Google phản hồi lỗi'
        ) from exc

    try:
        return response.json()

    except ValueError as exc:
        raise GoogleProviderUnavailableError(
            'Dịch vụ Google trả dữ liệu không hợp lệ'
        ) from exc


def get_google_identity(token):
    google_client_id = (
        getattr(
            settings,
            'GOOGLE_CLIENT_ID',
            '',
        )
        or getattr(
            settings,
            'GOOGLE_WEB_CLIENT_ID',
            '',
        )
        or os.getenv(
            'GOOGLE_CLIENT_ID',
            '',
        )
        or os.getenv(
            'GOOGLE_WEB_CLIENT_ID',
            '',
        )
    ).strip()

    if not google_client_id:
        logger.error(
            'Google Login chưa cấu hình Google Client ID'
        )

        raise GoogleProviderUnavailableError(
            'Google Login chưa được cấu hình'
        )

    try:
        identity = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            google_client_id,
        )

    except (
        ValueError,
        GoogleAuthError,
    ):
        token_info = request_google_json(
            'https://oauth2.googleapis.com/tokeninfo',
            params={
                'access_token': token,
            },
        )

        token_audience = (
            token_info.get('audience')
            or token_info.get('issued_to')
            or ''
        )

        if token_audience != google_client_id:
            raise GoogleTokenInvalidError(
                'Google token không thuộc ứng dụng'
            )

        identity = request_google_json(
            'https://www.googleapis.com/oauth2/v1/userinfo',
            params={
                'access_token': token,
            },
        )

    email = str(
        identity.get('email') or ''
    ).strip().lower()

    if not email:
        raise GoogleTokenInvalidError(
            'Không lấy được email Google'
        )

    email_verified = identity.get(
        'email_verified'
    )

    if email_verified is None:
        email_verified = identity.get(
            'verified_email'
        )

    if email_verified is not True:
        raise GoogleTokenInvalidError(
            'Email Google chưa được xác thực'
        )

    full_name = str(
        identity.get('name') or ''
    ).strip()

    return {
        'email': email,
        'full_name': full_name,
    }


def generate_otp():
    return str(
        random.randint(100000, 999999)
    )


def send_register_otp(email, otp):
    subject = 'Mã OTP xác thực tài khoản Chung Ví'

    text_content = (
        f'Mã OTP xác thực tài khoản của bạn là: {otp}\n\n'
        'OTP có hiệu lực trong 10 phút.'
    )

    html_content = f"""
    <div style="margin:0;padding:0;background:#f3f7f6;font-family:Arial,sans-serif;">
      <div style="max-width:560px;margin:0 auto;padding:32px 16px;">
        <div style="background:#ffffff;border-radius:20px;padding:32px;border:1px solid #e5eeee;">
          <div style="text-align:center;margin-bottom:24px;">
            <h1 style="margin:0;color:#0f8f6f;font-size:28px;font-weight:800;">
              Chung Ví
            </h1>
            <p style="margin:8px 0 0;color:#6b7280;font-size:14px;">
              Chia tiền nhóm dễ dàng hơn
            </p>
          </div>

          <h2 style="margin:0 0 12px;color:#111827;font-size:22px;">
            Xác thực email của bạn
          </h2>

          <p style="margin:0 0 20px;color:#4b5563;font-size:15px;line-height:1.6;">
            Cảm ơn bạn đã đăng ký Chung Ví. Vui lòng nhập mã OTP bên dưới để hoàn tất tạo tài khoản.
          </p>

          <div style="text-align:center;margin:28px 0;">
            <div style="display:inline-block;background:#ecfdf5;color:#047857;
                        font-size:34px;font-weight:800;letter-spacing:8px;
                        padding:18px 28px;border-radius:16px;border:1px solid #bbf7d0;">
              {otp}
            </div>
          </div>

          <p style="margin:0;color:#4b5563;font-size:15px;line-height:1.6;">
            Mã OTP có hiệu lực trong <strong>10 phút</strong>. Không chia sẻ mã này cho bất kỳ ai.
          </p>

          <div style="margin-top:28px;padding-top:20px;border-top:1px solid #e5eeee;">
            <p style="margin:0;color:#9ca3af;font-size:12px;line-height:1.5;">
              Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email.
            </p>
          </div>
        </div>
      </div>
    </div>
    """

    email_message = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )

    email_message.attach_alternative(
        html_content,
        "text/html",
    )

    email_message.send()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        email = serializer.validated_data[
            'email'
        ]

        existing_user = User.objects.filter(
            email=email,
            email_verified=False,
        ).first()

        if existing_user:
            user = existing_user
        else:
            user = serializer.save()

        otp = generate_otp()

        cache.set(
            f'register_otp:{user.email}',
            otp,
            timeout=OTP_EXPIRE_SECONDS,
        )

        cache.set(
            f'register_otp_attempts:{user.email}',
            0,
            timeout=OTP_EXPIRE_SECONDS,
        )

        cache.set(
            f'register_otp_cooldown:{user.email}',
            True,
            timeout=OTP_RESEND_COOLDOWN,
        )

        send_register_otp(
            user.email,
            otp,
        )

        return Response(
            {
                'message': (
                    'Đăng ký thành công. '
                    'Vui lòng xác thực email.'
                ),
                'email': user.email,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyRegisterOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyRegisterOTPSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        email = serializer.validated_data[
            'email'
        ].lower().strip()

        otp = serializer.validated_data[
            'otp'
        ]

        user = User.objects.filter(
            email=email
        ).first()

        otp_is_valid = consume_cached_otp(
            otp_key=f'register_otp:{email}',
            attempts_key=(
                f'register_otp_attempts:{email}'
            ),
            submitted_otp=otp,
        )

        if not user or not otp_is_valid:
            return Response(
                {
                    'detail': (
                        'OTP không hợp lệ, đã hết hạn '
                        'hoặc đã vượt quá số lần thử'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.email_verified = True
        user.is_active = True

        user.save()

        return Response(
            {
                'message':
                'Xác thực email thành công'
            },
            status=status.HTTP_200_OK,
        )

class ResendRegisterOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendRegisterOTPSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        email = serializer.validated_data[
            'email'
        ].lower().strip()

        cooldown_key = (
            f'register_otp_cooldown:{email}'
        )

        if cache.get(cooldown_key):
            return Response(
                {
                    'detail': (
                        'Vui lòng đợi 60 giây '
                        'để gửi lại OTP.'
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        cache.set(
            cooldown_key,
            True,
            timeout=OTP_RESEND_COOLDOWN,
        )

        user = User.objects.filter(
            email=email
        ).first()

        if user and not user.email_verified:
            otp = generate_otp()

            cache.set(
                f'register_otp:{email}',
                otp,
                timeout=OTP_EXPIRE_SECONDS,
            )

            cache.set(
                f'register_otp_attempts:{email}',
                0,
                timeout=OTP_EXPIRE_SECONDS,
            )

            send_register_otp(
                email,
                otp,
            )

        return Response(
            {
                'message': (
                    'Nếu email hợp lệ và chưa xác thực, '
                    'OTP sẽ được gửi.'
                )
            },
            status=status.HTTP_200_OK,
        )


class CustomTokenObtainPairSerializer(
    TokenObtainPairSerializer
):
    def validate(self, attrs):
        data = super().validate(attrs)

        if not self.user.email_verified:
            raise ValidationError(
                {
                    'detail':
                    'Email chưa được xác thực'
                }
            )

        return data


class CustomTokenObtainPairView(
    TokenObtainPairView
):
    serializer_class = (
        CustomTokenObtainPairSerializer
    )


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [
        JSONParser,
        MultiPartParser,
        FormParser,
    ]

    def get_object(self):
        return self.request.user
    
class UserAvatarView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, user_id):
        user = User.objects.filter(
            id=user_id
        ).only(
            'avatar_data',
            'avatar_content_type',
            'avatar_updated_at',
        ).first()

        if not user or not user.avatar_data:
            return Response(
                {
                    'detail': 'Không tìm thấy ảnh đại diện'
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        content_type = (
            user.avatar_content_type or
            'application/octet-stream'
        )

        response = HttpResponse(
            bytes(user.avatar_data),
            content_type=content_type,
        )

        if request.GET.get('v'):
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
        else:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response


class SaveFCMTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_token = request.data.get(
            'token'
        )

        if not isinstance(raw_token, str):
            return Response(
                {
                    'detail':
                    'Token phải là chuỗi ký tự'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = raw_token.strip()

        if not token:
            return Response(
                {
                    'detail':
                    'Token không được để trống'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(token) > FCM_TOKEN_MAX_LENGTH:
            return Response(
                {
                    'detail': (
                        'Token vượt quá độ dài '
                        'cho phép'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_device_type = request.data.get(
            'device_type',
            FCMDevice.DeviceType.ANDROID,
        )

        if not isinstance(
            raw_device_type,
            str,
        ):
            return Response(
                {
                    'detail': (
                        'Loại thiết bị phải là '
                        'chuỗi ký tự'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        device_type = (
            raw_device_type
            .strip()
            .lower()
        )

        if (
            device_type not in
            FCMDevice.DeviceType.values
        ):
            return Response(
                {
                    'detail': (
                        'Loại thiết bị chỉ chấp nhận '
                        'android, ios hoặc web'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        FCMDevice.objects.update_or_create(
            token=token,
            defaults={
                'user': request.user,
                'device_type': device_type,
            },
        )

        return Response(
            {
                'message':
                'FCM token saved successfully'
            },
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        user = request.user

        old_password = serializer.validated_data[
            'old_password'
        ]

        new_password = serializer.validated_data[
            'new_password'
        ]

        if not check_password(
            old_password,
            user.password
        ):
            return Response(
                {
                    'detail':
                    'Mật khẩu hiện tại không đúng'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if old_password == new_password:
            return Response(
                {
                    'detail':
                    'Mật khẩu mới không được trùng với mật khẩu hiện tại'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)

        user.save()

        return Response(
            {
                'message':
                'Đổi mật khẩu thành công'
            },
            status=status.HTTP_200_OK
        )


class ForgotPasswordRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = (
            ForgotPasswordRequestSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        email = serializer.validated_data[
            'email'
        ].lower().strip()

        cooldown_key = (
            f'forgot_password_otp_cooldown:{email}'
        )

        if cache.get(cooldown_key):
            return Response(
                {
                    'detail': (
                        'Vui lòng đợi 60 giây '
                        'trước khi yêu cầu OTP mới.'
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        cache.set(
            cooldown_key,
            True,
            timeout=FORGOT_PASSWORD_OTP_COOLDOWN,
        )

        user = User.objects.filter(
            email=email
        ).first()

        if user:
            otp = generate_otp()

            cache.set(
                f'forgot_password_otp:{email}',
                otp,
                timeout=OTP_EXPIRE_SECONDS,
            )

            cache.set(
                (
                    'forgot_password_otp_attempts:'
                    f'{email}'
                ),
                0,
                timeout=OTP_EXPIRE_SECONDS,
            )

            send_mail(
                subject=(
                    'Mã OTP đặt lại mật khẩu '
                    'Chung Ví'
                ),
                message=(
                    f'Mã OTP của bạn là: {otp}\n\n'
                    'OTP có hiệu lực trong 10 phút.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

        return Response(
            {
                'message': (
                    'Nếu email tồn tại, '
                    'OTP sẽ được gửi.'
                )
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        email = serializer.validated_data[
            'email'
        ].lower().strip()

        otp = serializer.validated_data[
            'otp'
        ]

        new_password = serializer.validated_data[
            'new_password'
        ]

        otp_is_valid = consume_cached_otp(
            otp_key=(
                f'forgot_password_otp:{email}'
            ),
            attempts_key=(
                'forgot_password_otp_attempts:'
                f'{email}'
            ),
            submitted_otp=otp,
        )

        user = User.objects.filter(
            email=email
        ).first()

        if not otp_is_valid or not user:
            return Response(
                {
                    'detail': (
                        'OTP không hợp lệ, đã hết hạn '
                        'hoặc đã vượt quá số lần thử'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(
            new_password
        )

        user.save()

        return Response(
            {
                'message':
                'Đặt lại mật khẩu thành công'
            },
            status=status.HTTP_200_OK,
        )


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get(
            'token'
        )

        if not isinstance(token, str):
            return Response(
                {
                    'detail':
                    'Thiếu token Google'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = token.strip()

        if not token:
            return Response(
                {
                    'detail':
                    'Thiếu token Google'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            identity = get_google_identity(
                token
            )

        except GoogleTokenInvalidError:
            return Response(
                {
                    'detail':
                    'Google token không hợp lệ'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except GoogleProviderUnavailableError:
            logger.exception(
                'Dịch vụ Google Login không khả dụng'
            )

            return Response(
                {
                    'detail': (
                        'Dịch vụ Google tạm thời '
                        'không khả dụng'
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        email = identity[
            'email'
        ]

        full_name = identity[
            'full_name'
        ]

        user = User.objects.filter(
            email=email
        ).first()

        if user and not user.is_active:
            return Response(
                {
                    'detail':
                    'Tài khoản đã bị vô hiệu hóa'
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user:
            user = User.objects.create(
                email=email,
                username=email,
                full_name=full_name,
                auth_provider='google',
                email_verified=True,
                is_active=True,
            )

            user.set_unusable_password()
            user.save()

        else:
            user.full_name = (
                user.full_name
                or full_name
            )

            user.auth_provider = 'google'
            user.email_verified = True

            user.save()

        refresh = RefreshToken.for_user(
            user
        )

        return Response(
            {
                'access': str(
                    refresh.access_token
                ),
                'refresh': str(
                    refresh
                ),
                'user': {
                    'email': user.email,
                    'full_name': user.full_name,
                },
            },
            status=status.HTTP_200_OK,
        )