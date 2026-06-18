import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'app_theme.dart';
import 'login_screen.dart';
import 'services/api_service.dart';

class VerifyRegisterOTPScreen extends StatefulWidget {
  final String email;

  const VerifyRegisterOTPScreen({super.key, required this.email});

  @override
  State<VerifyRegisterOTPScreen> createState() =>
      _VerifyRegisterOTPScreenState();
}

class _VerifyRegisterOTPScreenState extends State<VerifyRegisterOTPScreen> {
  static const otpLength = 6;
  static const resendCooldownSeconds = 60;

  final List<TextEditingController> otpControllers = List.generate(
    otpLength,
    (_) => TextEditingController(),
  );

  final List<FocusNode> otpFocusNodes = List.generate(
    otpLength,
    (_) => FocusNode(),
  );

  bool isLoading = false;
  bool isResending = false;
  bool isVerified = false;

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

  Future<void> verifyOTP() async {
    if (isLoading || isVerified) return;

    final otp = getOTP();

    if (otp.length != otpLength) {
      showMessage('Vui lòng nhập đủ 6 số OTP');
      return;
    }

    try {
      setState(() {
        isLoading = true;
      });

      await ApiService.verifyRegisterOTP(email: widget.email, otp: otp);

      if (!mounted) return;

      setState(() {
        isVerified = true;
      });

      showMessage('Xác thực email thành công');

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
      } else {
        showMessage('Xác thực OTP thất bại');
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

  Future<void> resendOTP() async {
    if (isResending || isLoading || resendSeconds > 0) {
      return;
    }

    try {
      setState(() {
        isResending = true;
      });

      await ApiService.resendRegisterOTP(email: widget.email);

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
          enabled: !isLoading && !isVerified,
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
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(16),
              borderSide: const BorderSide(color: Color(0xFFDDE7EA)),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(16),
              borderSide: const BorderSide(color: Color(0xFFDDE7EA)),
            ),
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
                verifyOTP();
              }
            }
          },
        ),
      ),
    );
  }

  Widget buildVerifyButton() {
    return SizedBox(
      width: double.infinity,
      height: 56,
      child: ElevatedButton(
        onPressed: isLoading || isVerified ? null : verifyOTP,
        style: ElevatedButton.styleFrom(
          elevation: 0,
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          disabledBackgroundColor: AppColors.primary.withValues(alpha: 0.45),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
        ),
        child: isVerified
            ? const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.check_circle_rounded, color: Colors.white),
                  SizedBox(width: 8),
                  Text(
                    'Xác thực thành công',
                    style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900),
                  ),
                ],
              )
            : isLoading
            ? const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  color: Colors.white,
                ),
              )
            : const Text(
                'Xác thực',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900),
              ),
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
                  AnimatedSwitcher(
                    duration: const Duration(milliseconds: 250),
                    child: isVerified
                        ? const Icon(
                            Icons.verified_rounded,
                            key: ValueKey('verified'),
                            size: 72,
                            color: AppColors.primary,
                          )
                        : const Icon(
                            Icons.mark_email_read_rounded,
                            key: ValueKey('email'),
                            size: 72,
                            color: AppColors.primary,
                          ),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Xác thực email',
                    style: TextStyle(
                      fontSize: 26,
                      fontWeight: FontWeight.w900,
                      color: AppColors.textDark,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'Mã OTP đã được gửi tới\n${widget.email}',
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
                  const SizedBox(height: 22),
                  buildVerifyButton(),
                  const SizedBox(height: 12),
                  buildResendButton(),
                  const SizedBox(height: 8),
                  const Text(
                    'OTP có hiệu lực trong 10 phút. Không chia sẻ mã này cho bất kỳ ai.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: AppColors.textLight,
                      fontSize: 12.5,
                      fontWeight: FontWeight.w600,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
