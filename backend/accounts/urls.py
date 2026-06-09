from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from accounts.views import (
    RegisterView,
    SaveFCMTokenView,
    UserProfileView,
    UserAvatarView,
    ChangePasswordView,
    ForgotPasswordRequestView,
    ResetPasswordView,
    GoogleLoginView,
    VerifyRegisterOTPView,
    ResendRegisterOTPView,
    CustomTokenObtainPairView,
)


urlpatterns = [
    path(
        'register/',
        RegisterView.as_view(),
    ),

    path(
        'verify-register-otp/',
        VerifyRegisterOTPView.as_view(),
    ),

    path(
        'resend-register-otp/',
        ResendRegisterOTPView.as_view(),
    ),

    path(
        'login/',
        CustomTokenObtainPairView.as_view(),
    ),

    path(
        'refresh/',
        TokenRefreshView.as_view(),
    ),

    path(
        'profile/',
        UserProfileView.as_view(),
    ),

    path(
        'users/<int:user_id>/avatar/',
        UserAvatarView.as_view(),
        name='user-avatar',
    ),

    path(
        'save-fcm-token/',
        SaveFCMTokenView.as_view(),
    ),

    path(
        'change-password/',
        ChangePasswordView.as_view(),
    ),

    path(
        'forgot-password/',
        ForgotPasswordRequestView.as_view(),
    ),

    path(
        'reset-password/',
        ResetPasswordView.as_view(),
    ),

    path(
        'google-login/',
        GoogleLoginView.as_view(),
    ),
]