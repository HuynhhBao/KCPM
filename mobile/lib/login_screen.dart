import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';

import 'app_theme.dart';
import 'bottom_nav_screen.dart';
import 'register_screen.dart';
import 'services/api_service.dart';
import 'package:dio/dio.dart';
import 'forgot_password_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final emailController = TextEditingController();
  final passwordController = TextEditingController();

  bool isLoading = false;
  bool hidePassword = true;

  bool get showAppleLogin {
    if (kIsWeb) return false;

    return defaultTargetPlatform == TargetPlatform.iOS;
  }

  static const Color darkGreen = AppColors.primary;
  static const Color deepGreen = AppColors.primary;

  @override
  void dispose() {
    emailController.dispose();
    passwordController.dispose();
    super.dispose();
  }

  Future<void> login() async {
    final email = emailController.text.trim();
    final password = passwordController.text.trim();

    if (email.isEmpty || password.isEmpty) {
      showMessage('Vui lòng nhập email và mật khẩu');
      return;
    }

    try {
      setState(() => isLoading = true);

      final response = await ApiService.login(email: email, password: password);

      final access = response.data['access'];
      final refresh = response.data['refresh'];

      if (access == null || refresh == null) {
        throw Exception('Token không hợp lệ');
      }

      await ApiService.saveTokens(
        access: access.toString(),
        refresh: refresh.toString(),
        email: email,
      );

      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const BottomNavScreen()),
      );
    } on DioException catch (e) {
      debugPrint('LOGIN ERROR: $e');

      final data = e.response?.data;

      if (data is Map && data['detail'] != null) {
        showMessage(data['detail'].toString());
      } else {
        showMessage('Email hoặc mật khẩu không đúng');
      }
    } catch (e) {
      debugPrint('LOGIN ERROR: $e');
      showMessage('Không thể kết nối máy chủ');
    } finally {
      if (mounted) {
        setState(() => isLoading = false);
      }
    }
  }

  Future<void> loginWithGoogle() async {
    try {
      setState(() => isLoading = true);

      await ApiService.loginWithGoogle();

      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const BottomNavScreen()),
      );
    } catch (e) {
      debugPrint('GOOGLE LOGIN ERROR: $e');
      showMessage('Đăng nhập Google thất bại');
    } finally {
      if (mounted) {
        setState(() => isLoading = false);
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

  Widget buildLogoHeader(bool compact) {
    final logoSize = compact ? 70.0 : 84.0;

    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Container(
          width: logoSize,
          height: logoSize,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(26),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.20),
                blurRadius: 30,
                offset: const Offset(0, 14),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(26),
            child: Image.asset('assets/images/logo.jpg', fit: BoxFit.cover),
          ),
        ),
        SizedBox(height: compact ? 12 : 16),
        const Text(
          'Chung Ví',
          style: TextStyle(
            color: Colors.white,
            fontSize: 34,
            fontWeight: FontWeight.w900,
            letterSpacing: -0.8,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'Chia tiền nhóm dễ dàng hơn',
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.76),
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget buildInput({
    required String label,
    required String hint,
    required IconData icon,
    required TextEditingController controller,
    bool obscure = false,
    Widget? suffixIcon,
    TextInputType? keyboardType,
    TextInputAction? textInputAction,
    void Function(String)? onSubmitted,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: AppColors.textDark,
            fontSize: 15,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 54,
          child: TextField(
            controller: controller,
            obscureText: obscure,
            keyboardType: keyboardType,
            textInputAction: textInputAction,
            onSubmitted: onSubmitted,
            style: const TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w700,
              color: AppColors.textDark,
            ),
            decoration: InputDecoration(
              hintText: hint,
              filled: true,
              fillColor: const Color(0xFFF7FAFA),
              prefixIcon: Icon(icon, color: AppColors.textLight, size: 21),
              suffixIcon: suffixIcon,
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 14,
              ),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(19),
                borderSide: const BorderSide(color: Color(0xFFDDE7EA)),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(19),
                borderSide: const BorderSide(color: Color(0xFFDDE7EA)),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(19),
                borderSide: const BorderSide(color: darkGreen, width: 1.5),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget buildLoginButton() {
    return SizedBox(
      width: double.infinity,
      height: 56,
      child: ElevatedButton(
        onPressed: isLoading ? null : login,
        style: ElevatedButton.styleFrom(
          elevation: 0,
          backgroundColor: darkGreen,
          disabledBackgroundColor: darkGreen.withValues(alpha: 0.35),
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            if (isLoading)
              const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2.2,
                  color: Colors.white,
                ),
              ),

            if (isLoading) const SizedBox(width: 10),

            Flexible(
              child: Text(
                isLoading ? 'Đang đăng nhập...' : 'Đăng nhập',
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget buildSocialCircle({
    required Widget icon,
    required VoidCallback? onTap,
  }) {
    return InkWell(
      onTap: isLoading ? null : onTap,
      borderRadius: BorderRadius.circular(999),
      child: Container(
        width: 58,
        height: 58,
        decoration: BoxDecoration(
          color: Colors.white,
          shape: BoxShape.circle,
          border: Border.all(color: const Color(0xFFE2EAED)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.08),
              blurRadius: 16,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        alignment: Alignment.center,
        child: icon,
      ),
    );
  }

  Widget buildGoogleIcon() {
    return Image.asset(
      'assets/images/google_logo.png',
      width: 30,
      height: 30,
      fit: BoxFit.contain,
    );
  }

  Widget buildDividerText() {
    return Row(
      children: [
        const Expanded(child: Divider(color: Color(0xFFDDE7EA), thickness: 1)),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          child: Text(
            'hoặc',
            style: TextStyle(
              color: AppColors.textLight.withValues(alpha: 0.9),
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        const Expanded(child: Divider(color: Color(0xFFDDE7EA), thickness: 1)),
      ],
    );
  }

  Widget buildRegisterHint() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Text(
          'Chưa có tài khoản?',
          style: TextStyle(
            color: AppColors.textLight,
            fontWeight: FontWeight.w600,
          ),
        ),
        TextButton(
          onPressed: isLoading
              ? null
              : () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const RegisterScreen()),
                  );
                },
          child: const Text(
            'Đăng ký',
            style: TextStyle(color: darkGreen, fontWeight: FontWeight.w900),
          ),
        ),
      ],
    );
  }

  Widget buildLoginCard(bool compact) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.fromLTRB(24, compact ? 24 : 30, 24, 18),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(34)),
      ),
      child: Column(
        children: [
          buildInput(
            label: 'Email',
            hint: 'Nhập email của bạn',
            icon: Icons.mail_outline_rounded,
            controller: emailController,
            keyboardType: TextInputType.emailAddress,
            textInputAction: TextInputAction.next,
          ),
          SizedBox(height: compact ? 12 : 16),
          buildInput(
            label: 'Mật khẩu',
            hint: 'Nhập mật khẩu',
            icon: Icons.lock_outline_rounded,
            controller: passwordController,
            obscure: hidePassword,
            textInputAction: TextInputAction.done,
            onSubmitted: (_) => login(),
            suffixIcon: IconButton(
              onPressed: () {
                setState(() {
                  hidePassword = !hidePassword;
                });
              },
              icon: Icon(
                hidePassword
                    ? Icons.visibility_off_outlined
                    : Icons.visibility_outlined,
                color: AppColors.textLight,
              ),
            ),
          ),
          SizedBox(height: compact ? 4 : 8),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: isLoading
                  ? null
                  : () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => const ForgotPasswordScreen(),
                        ),
                      );
                    },
              child: const Text(
                'Quên mật khẩu?',
                style: TextStyle(
                  color: AppColors.primary,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
          ),
          SizedBox(height: compact ? 4 : 8),
          buildLoginButton(),
          SizedBox(height: compact ? 18 : 22),
          buildDividerText(),
          SizedBox(height: compact ? 14 : 18),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              buildSocialCircle(
                icon: buildGoogleIcon(),
                onTap: loginWithGoogle,
              ),
              const SizedBox(width: 22),
              buildSocialCircle(
                icon: const Icon(
                  Icons.facebook_rounded,
                  color: Color(0xFF1877F2),
                  size: 32,
                ),
                onTap: () {
                  showMessage('Facebook Login sẽ mở rộng sau');
                },
              ),
              if (showAppleLogin) ...[
                const SizedBox(width: 22),
                buildSocialCircle(
                  icon: const Icon(
                    Icons.apple_rounded,
                    color: Colors.black,
                    size: 34,
                  ),
                  onTap: () {
                    showMessage('Apple Login sẽ mở rộng sau');
                  },
                ),
              ],
            ],
          ),
          SizedBox(height: compact ? 14 : 20),
          const Spacer(),
          buildRegisterHint(),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      resizeToAvoidBottomInset: true,
      backgroundColor: deepGreen,
      body: GestureDetector(
        onTap: () => FocusScope.of(context).unfocus(),
        child: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [
                AppColors.primaryLight,
                AppColors.primary,
                AppColors.primary,
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
          child: SafeArea(
            bottom: false,
            child: LayoutBuilder(
              builder: (context, constraints) {
                final compact = constraints.maxHeight < 760;

                return AnimatedPadding(
                  duration: const Duration(milliseconds: 250),
                  curve: Curves.easeOut,
                  padding: EdgeInsets.only(
                    bottom: MediaQuery.of(context).viewInsets.bottom * 0.45,
                  ),
                  child: SizedBox(
                    width: double.infinity,
                    child: Column(
                      children: [
                        Expanded(
                          flex: compact ? 32 : 36,
                          child: buildLogoHeader(compact),
                        ),
                        Flexible(
                          flex: compact ? 68 : 64,
                          child: buildLoginCard(compact),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}
