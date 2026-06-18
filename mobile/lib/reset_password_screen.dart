import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'app_theme.dart';
import 'login_screen.dart';
import 'services/api_service.dart';

class ResetPasswordScreen extends StatefulWidget {
  final String email;

  const ResetPasswordScreen({super.key, required this.email});

  @override
  State<ResetPasswordScreen> createState() => _ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends State<ResetPasswordScreen> {
  static const otpLength = 6;
  static const resendCooldownSeconds = 60;

  final otpControllers = List.generate(
    otpLength,
    (_) => TextEditingController(),
  );

  final otpFocusNodes = List.generate(otpLength, (_) => FocusNode());

  final passwordController = TextEditingController();
  final confirmPasswordController = TextEditingController();

  bool isLoading = false;
  bool isResending = false;
  bool isSuccess = false;
  bool hidePassword = true;
  bool hideConfirmPassword = true;

  int resendSeconds = resendCooldownSeconds;
  Timer? resendTimer;

  @override
  void initState() {
    super.initState();
    startResendCountdown();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        otpFocusNodes.first.requestFocus();
      }
    });
  }

  @override
  void dispose() {
    resendTimer?.cancel();

    for (final controller in otpControllers) {
      controller.dispose();
    }

    for (final node in otpFocusNodes) {
      node.dispose();
    }

    passwordController.dispose();
    confirmPasswordController.dispose();

    super.dispose();
  }

  void startResendCountdown() {
    resendTimer?.cancel();

    setState(() {
      resendSeconds = resendCooldownSeconds;
    });

    resendTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) return;

      if (resendSeconds <= 1) {
        timer.cancel();

        setState(() {
          resendSeconds = 0;
        });
      } else {
        setState(() {
          resendSeconds--;
        });
      }
    });
  }

  String getOTP() {
    return otpControllers.map((controller) => controller.text.trim()).join();
  }

  void clearOTP() {
    for (final controller in otpControllers) {
      controller.clear();
    }

    otpFocusNodes.first.requestFocus();
  }

  Future<void> resendOTP() async {
    if (isResending || isLoading || resendSeconds > 0) {
      return;
    }

    try {
      setState(() {
        isResending = true;
      });

      await ApiService.forgotPassword(email: widget.email);

      if (!mounted) return;

      clearOTP();
      startResendCountdown();
      showMessage('OTP đã được gửi lại');
    } on DioException catch (e) {
      final data = e.response?.data;

      if (data is Map && data['detail'] != null) {
        showMessage(data['detail'].toString());
      } else {
        showMessage('Không thể gửi lại OTP');
      }
    } catch (_) {
      showMessage('Không thể kết nối máy chủ');
    } finally {
      if (mounted) {
        setState(() {
          isResending = false;
        });
      }
    }
  }

  Future<void> resetPassword() async {
    if (isLoading || isSuccess) return;

    final otp = getOTP();
    final password = passwordController.text.trim();
    final confirmPassword = confirmPasswordController.text.trim();

    if (otp.length != otpLength) {
      showMessage('Vui lòng nhập đủ 6 số OTP');
      return;
    }

    if (password.length < 8) {
      showMessage('Mật khẩu phải có ít nhất 8 ký tự');
      return;
    }

    if (password != confirmPassword) {
      showMessage('Mật khẩu xác nhận không khớp');
      return;
    }

    try {
      setState(() {
        isLoading = true;
      });

      await ApiService.resetPassword(
        email: widget.email,
        otp: otp,
        newPassword: password,
        confirmPassword: confirmPassword,
      );

      if (!mounted) return;

      setState(() {
        isSuccess = true;
      });

      showMessage('Đặt lại mật khẩu thành công');

      await Future.delayed(const Duration(milliseconds: 900));

      if (!mounted) return;

      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (route) => false,
      );
    } on DioException catch (e) {
      final data = e.response?.data;

      if (data is Map && data['detail'] != null) {
        showMessage(data['detail'].toString());
      } else if (data is Map && data['confirm_password'] != null) {
        showMessage(data['confirm_password'].toString());
      } else {
        showMessage('Đặt lại mật khẩu thất bại');
      }

      clearOTP();
    } catch (_) {
      showMessage('Không thể kết nối máy chủ');
    } finally {
      if (mounted) {
        setState(() {
          isLoading = false;
        });
      }
    }
  }

  void showMessage(String message) {
    if (!mounted) return;

    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(content: Text(message), behavior: SnackBarBehavior.floating),
      );
  }

  Widget buildOTPBox(int index) {
    return SizedBox(
      width: 48,
      height: 58,
      child: KeyboardListener(
        focusNode: FocusNode(),
        onKeyEvent: (event) {
          if (event is KeyDownEvent &&
              event.logicalKey == LogicalKeyboardKey.backspace &&
              otpControllers[index].text.isEmpty &&
              index > 0) {
            otpFocusNodes[index - 1].requestFocus();
            otpControllers[index - 1].clear();
          }
        },
        child: TextField(
          controller: otpControllers[index],
          focusNode: otpFocusNodes[index],
          enabled: !isLoading && !isSuccess,
          textAlign: TextAlign.center,
          keyboardType: TextInputType.number,
          maxLength: 1,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          style: const TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w900,
            color: AppColors.textDark,
          ),
          decoration: InputDecoration(
            counterText: '',
            filled: true,
            fillColor: const Color(0xFFF7FAFA),
            contentPadding: EdgeInsets.zero,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(16)),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(16),
              borderSide: const BorderSide(
                color: AppColors.primary,
                width: 1.8,
              ),
            ),
          ),
          onChanged: (value) {
            if (value.isNotEmpty) {
              if (index < otpLength - 1) {
                otpFocusNodes[index + 1].requestFocus();
              } else {
                FocusScope.of(context).unfocus();
              }
            }
          },
        ),
      ),
    );
  }

  Widget buildPasswordInput({
    required String hint,
    required TextEditingController controller,
    required bool obscure,
    required VoidCallback onToggle,
  }) {
    return TextField(
      controller: controller,
      obscureText: obscure,
      textInputAction: TextInputAction.next,
      decoration: InputDecoration(
        hintText: hint,
        prefixIcon: const Icon(Icons.lock_outline_rounded),
        suffixIcon: IconButton(
          onPressed: onToggle,
          icon: Icon(
            obscure ? Icons.visibility_off_outlined : Icons.visibility_outlined,
          ),
        ),
        filled: true,
        fillColor: const Color(0xFFF7FAFA),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(18)),
      ),
    );
  }

  Widget buildResendButton() {
    final canResend = resendSeconds == 0 && !isResending && !isLoading;

    return TextButton(
      onPressed: canResend ? resendOTP : null,
      child: Text(
        isResending
            ? 'Đang gửi lại...'
            : resendSeconds > 0
            ? 'Gửi lại OTP sau ${resendSeconds}s'
            : 'Gửi lại OTP',
        style: TextStyle(
          fontWeight: FontWeight.w900,
          color: canResend ? AppColors.primary : AppColors.textLight,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Container(
              width: double.infinity,
              constraints: const BoxConstraints(maxWidth: 520),
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(28),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    isSuccess
                        ? Icons.check_circle_rounded
                        : Icons.password_rounded,
                    size: 72,
                    color: AppColors.primary,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Đặt lại mật khẩu',
                    style: TextStyle(
                      fontSize: 26,
                      fontWeight: FontWeight.w900,
                      color: AppColors.textDark,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'Nhập OTP đã gửi tới\n${widget.email}',
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: AppColors.textLight,
                      fontWeight: FontWeight.w600,
                      height: 1.45,
                    ),
                  ),
                  const SizedBox(height: 26),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: List.generate(otpLength, buildOTPBox),
                  ),
                  const SizedBox(height: 18),
                  buildPasswordInput(
                    hint: 'Mật khẩu mới',
                    controller: passwordController,
                    obscure: hidePassword,
                    onToggle: () {
                      setState(() {
                        hidePassword = !hidePassword;
                      });
                    },
                  ),
                  const SizedBox(height: 14),
                  buildPasswordInput(
                    hint: 'Xác nhận mật khẩu mới',
                    controller: confirmPasswordController,
                    obscure: hideConfirmPassword,
                    onToggle: () {
                      setState(() {
                        hideConfirmPassword = !hideConfirmPassword;
                      });
                    },
                  ),
                  const SizedBox(height: 22),
                  SizedBox(
                    width: double.infinity,
                    height: 56,
                    child: ElevatedButton(
                      onPressed: isLoading || isSuccess ? null : resetPassword,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(20),
                        ),
                      ),
                      child: isLoading
                          ? const SizedBox(
                              width: 22,
                              height: 22,
                              child: CircularProgressIndicator(
                                strokeWidth: 2.5,
                                color: Colors.white,
                              ),
                            )
                          : Text(
                              isSuccess ? 'Thành công' : 'Đặt lại mật khẩu',
                              style: const TextStyle(
                                fontSize: 17,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  buildResendButton(),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
