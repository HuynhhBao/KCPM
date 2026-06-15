import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';

import 'app_theme.dart';
import 'bottom_nav_screen.dart';
import 'firebase_options.dart';
import 'login_screen.dart';
import 'services/api_service.dart';
import 'widgets/app_loading_state.dart';

final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

  await ApiService.init();

  runApp(const MyApp());
}

class MyApp extends StatefulWidget {
  const MyApp({super.key});

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  bool isCheckingAuth = true;
  bool isLoggedIn = false;

  @override
  void initState() {
    super.initState();

    checkLogin();

    setupFirebaseMessaging();
  }

  Future<void> checkLogin() async {
    final authenticated = await ApiService.checkAuth();

    if (!mounted) return;

    setState(() {
      isLoggedIn = authenticated;
      isCheckingAuth = false;
    });
  }

  Future<void> setupFirebaseMessaging() async {
    debugPrint('SETUP FIREBASE START');

    if (kIsWeb) {
      debugPrint('SKIP FCM ON WEB');
      return;
    }

    try {
      final messaging = FirebaseMessaging.instance;

      await messaging.requestPermission(alert: true, badge: true, sound: true);

      final token = await messaging.getToken();

      debugPrint('FCM TOKEN: $token');

      if (token != null) {
        await ApiService.saveFCMToken(token);
      }

      FirebaseMessaging.onMessage.listen((message) {
        debugPrint('FOREGROUND MESSAGE: ${message.notification?.title}');
      });

      FirebaseMessaging.onMessageOpenedApp.listen((message) {
        debugPrint('NOTIFICATION CLICKED');
      });
    } catch (e) {
      debugPrint('FCM ERROR: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: navigatorKey,
      debugShowCheckedModeBanner: false,
      title: 'Chung Ví',
      theme: AppTheme.lightTheme,
      home: isCheckingAuth
          ? const Scaffold(
              backgroundColor: AppColors.background,
              body: AppLoadingState(
                message: 'Đang kiểm tra phiên đăng nhập...',
              ),
            )
          : isLoggedIn
          ? const BottomNavScreen()
          : const LoginScreen(),
    );
  }
}
