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

from django.contrib.auth.hashers import check_password
import random
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.contrib.auth import get_user_model

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

User = get_user_model()

OTP_EXPIRE_SECONDS = 600
OTP_RESEND_COOLDOWN = 60


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
        ].lower()

        otp = serializer.validated_data[
            'otp'
        ]

        user = User.objects.filter(
            email=email
        ).first()

        if not user:
            return Response(
                {
                    'detail':
                    'Người dùng không tồn tại'
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        cached_otp = cache.get(
            f'register_otp:{email}'
        )

        if not cached_otp:
            return Response(
                {
                    'detail':
                    'OTP đã hết hạn'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if cached_otp != otp:
            return Response(
                {
                    'detail':
                    'OTP không chính xác'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.email_verified = True
        user.is_active = True

        user.save()

        cache.delete(
            f'register_otp:{email}'
        )

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
        serializer = (
            ResendRegisterOTPSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        email = serializer.validated_data[
            'email'
        ].lower()

        user = User.objects.filter(
            email=email
        ).first()

        if not user:
            return Response(
                {
                    'message':
                    'Nếu email tồn tại OTP sẽ được gửi.'
                },
                status=status.HTTP_200_OK,
            )

        if user.email_verified:
            return Response(
                {
                    'detail':
                    'Email đã xác thực'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        cooldown = cache.get(
            f'register_otp_cooldown:{email}'
        )

        if cooldown:
            return Response(
                {
                    'detail': (
                        'Vui lòng đợi 60 giây '
                        'để gửi lại OTP.'
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        otp = generate_otp()

        cache.set(
            f'register_otp:{email}',
            otp,
            timeout=OTP_EXPIRE_SECONDS,
        )

        cache.set(
            f'register_otp_cooldown:{email}',
            True,
            timeout=OTP_RESEND_COOLDOWN,
        )

        send_register_otp(
            email,
            otp,
        )

        return Response(
            {
                'message':
                'OTP đã được gửi lại.'
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


class SaveFCMTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('token')

        if not token:
            return Response(
                {'detail': 'Token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        FCMDevice.objects.update_or_create(
            token=token,
            defaults={
                'user': request.user,
                'device_type': request.data.get(
                    'device_type',
                    'android'
                ),
            }
        )

        return Response(
            {'message': 'FCM token saved successfully'},
            status=status.HTTP_200_OK
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
        ].lower()

        user = User.objects.filter(
            email=email
        ).first()

        if not user:
            return Response(
                {
                    'message':
                    'Nếu email tồn tại, OTP sẽ được gửi.'
                },
                status=status.HTTP_200_OK
            )

        otp = str(
            random.randint(100000, 999999)
        )

        cache.set(
            f'forgot_password_otp:{email}',
            otp,
            timeout=600
        )

        send_mail(
            subject='Mã OTP đặt lại mật khẩu Chung Ví',
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
                'message':
                'OTP đã được gửi tới email.'
            },
            status=status.HTTP_200_OK
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
        ].lower()

        otp = serializer.validated_data[
            'otp'
        ]

        new_password = serializer.validated_data[
            'new_password'
        ]

        cached_otp = cache.get(
            f'forgot_password_otp:{email}'
        )

        if not cached_otp:
            return Response(
                {
                    'detail':
                    'OTP đã hết hạn'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if cached_otp != otp:
            return Response(
                {
                    'detail':
                    'OTP không chính xác'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(
            email=email
        ).first()

        if not user:
            return Response(
                {
                    'detail':
                    'Người dùng không tồn tại'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        user.set_password(new_password)

        user.save()

        cache.delete(
            f'forgot_password_otp:{email}'
        )

        return Response(
            {
                'message':
                'Đặt lại mật khẩu thành công'
            },
            status=status.HTTP_200_OK
        )


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')

        if not token:
            return Response(
                {
                    'detail': 'Thiếu token Google'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            try:
                idinfo = id_token.verify_oauth2_token(
                    token,
                    requests.Request(),
                )

            except Exception:
                userinfo_response = pyrequests.get(
                    'https://www.googleapis.com/oauth2/v1/userinfo',
                    params={
                        'access_token': token
                    }
                )

                idinfo = userinfo_response.json()

            email = idinfo.get('email')

            if not email:
                return Response(
                    {
                        'detail': 'Không lấy được email'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            full_name = idinfo.get(
                'name',
                ''
            )

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'full_name': full_name,
                    'auth_provider': 'google',
                    'email_verified': True,
                    'is_active': True,
                }
            )

            if created:
                user.set_unusable_password()

            user.full_name = user.full_name or full_name
            user.auth_provider = 'google'
            user.email_verified = True
            user.is_active = True
            user.save()

            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    'access': str(
                        refresh.access_token
                    ),

                    'refresh': str(refresh),

                    'user': {
                        'email': user.email,
                        'full_name':
                        user.full_name,
                    }
                }
            )

        except Exception as e:
            print(e)

            return Response(
                {
                    'detail':
                    'Google token không hợp lệ'
                },
                status=status.HTTP_400_BAD_REQUEST
            )