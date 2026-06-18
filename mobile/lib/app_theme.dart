import 'package:flutter/material.dart';

class AppColors {
  static const Color primary = Color(0xFF0AAE7A);
  static const Color primaryDark = Color(0xFF066B55);
  static const Color primaryLight = Color(0xFF34C98F);

  static const Color secondary = Color(0xFF47B99A);

  static const Color background = Color(0xFFF4F8F5);
  static const Color backgroundWarm = Color(0xFFEAF7F1);
  static const Color surface = Colors.white;
  static const Color surfaceTint = Color(0xFFF8FCFA);

  static const Color textDark = Color(0xFF111827);
  static const Color textLight = Color(0xFF6B7280);
  static const Color textMuted = Color(0xFF8A938F);

  static const Color border = Color(0xFFE5E7EB);
  static const Color borderStrong = Color(0xFFD6E6DF);

  static const Color success = Color(0xFF159B5F);
  static const Color danger = Color(0xFFC84A5E);
  static const Color warning = Color(0xFFD58A22);
  static const Color info = Color(0xFF247C92);
}

class AppRadii {
  static const double small = 14;
  static const double medium = 18;
  static const double large = 24;
  static const double xlarge = 30;
}

class AppTheme {
  static ThemeData get lightTheme {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: AppColors.primary,
      brightness: Brightness.light,
      primary: AppColors.primary,
      secondary: AppColors.secondary,
      surface: AppColors.surface,
      error: AppColors.danger,
    );

    const String? baseFont = null;
    const textTheme = TextTheme(
      displaySmall: TextStyle(
        fontFamily: baseFont,
        color: AppColors.textDark,
        fontSize: 34,
        fontWeight: FontWeight.w900,
        height: 1.05,
        letterSpacing: -0.7,
      ),
      headlineMedium: TextStyle(
        fontFamily: baseFont,
        color: AppColors.textDark,
        fontSize: 28,
        fontWeight: FontWeight.w900,
        height: 1.08,
        letterSpacing: -0.55,
      ),
      headlineSmall: TextStyle(
        fontFamily: baseFont,
        color: AppColors.textDark,
        fontSize: 22,
        fontWeight: FontWeight.w900,
        height: 1.12,
        letterSpacing: -0.3,
      ),
      titleLarge: TextStyle(
        fontFamily: baseFont,
        color: AppColors.textDark,
        fontSize: 20,
        fontWeight: FontWeight.w800,
        height: 1.2,
      ),
      titleMedium: TextStyle(
        fontFamily: baseFont,
        color: AppColors.textDark,
        fontSize: 16,
        fontWeight: FontWeight.w800,
        height: 1.25,
      ),
      bodyLarge: TextStyle(
        fontFamily: baseFont,
        color: AppColors.textDark,
        fontSize: 16,
        fontWeight: FontWeight.w600,
        height: 1.45,
      ),
      bodyMedium: TextStyle(
        fontFamily: baseFont,
        color: AppColors.textLight,
        fontSize: 14,
        fontWeight: FontWeight.w600,
        height: 1.45,
      ),
      labelLarge: TextStyle(
        fontFamily: baseFont,
        fontSize: 15,
        fontWeight: FontWeight.w800,
      ),
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: AppColors.background,
      fontFamily: baseFont,
      textTheme: textTheme,
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.background,
        foregroundColor: AppColors.textDark,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          fontFamily: baseFont,
          color: AppColors.textDark,
          fontSize: 20,
          fontWeight: FontWeight.w900,
          letterSpacing: -0.3,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surfaceTint,
        hintStyle: const TextStyle(
          color: AppColors.textMuted,
          fontWeight: FontWeight.w600,
        ),
        labelStyle: const TextStyle(
          color: AppColors.textLight,
          fontWeight: FontWeight.w700,
        ),
        prefixIconColor: AppColors.textLight,
        suffixIconColor: AppColors.textLight,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 15,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.medium),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.medium),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.medium),
          borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.medium),
          borderSide: const BorderSide(color: AppColors.danger),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          elevation: 0,
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          disabledBackgroundColor: AppColors.primary.withValues(alpha: 0.34),
          disabledForegroundColor: Colors.white.withValues(alpha: 0.82),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
          textStyle: const TextStyle(
            fontFamily: baseFont,
            fontSize: 15,
            fontWeight: FontWeight.w900,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadii.medium),
          ),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          disabledBackgroundColor: AppColors.primary.withValues(alpha: 0.34),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
          textStyle: const TextStyle(
            fontFamily: baseFont,
            fontWeight: FontWeight.w900,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadii.medium),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.primary,
          side: const BorderSide(color: AppColors.borderStrong),
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          textStyle: const TextStyle(
            fontFamily: baseFont,
            fontWeight: FontWeight.w800,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadii.medium),
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.primary,
          textStyle: const TextStyle(
            fontFamily: baseFont,
            fontWeight: FontWeight.w900,
          ),
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: AppColors.surface,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.large),
        ),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: AppColors.surface,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.large),
        ),
        titleTextStyle: const TextStyle(
          fontFamily: baseFont,
          color: AppColors.textDark,
          fontSize: 20,
          fontWeight: FontWeight.w900,
        ),
        contentTextStyle: const TextStyle(
          fontFamily: baseFont,
          color: AppColors.textLight,
          fontSize: 14,
          fontWeight: FontWeight.w600,
          height: 1.45,
        ),
      ),
      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: AppColors.surface,
        surfaceTintColor: Colors.transparent,
        modalBackgroundColor: AppColors.surface,
        modalBarrierColor: Color(0x66061310),
      ),
      popupMenuTheme: PopupMenuThemeData(
        color: AppColors.surface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.medium),
          side: const BorderSide(color: AppColors.border),
        ),
        textStyle: const TextStyle(
          fontFamily: baseFont,
          color: AppColors.textDark,
          fontWeight: FontWeight.w700,
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: AppColors.textDark,
        contentTextStyle: const TextStyle(
          fontFamily: baseFont,
          color: Colors.white,
          fontWeight: FontWeight.w700,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.small),
        ),
      ),
      tabBarTheme: const TabBarThemeData(
        labelColor: AppColors.primary,
        unselectedLabelColor: AppColors.textLight,
        indicatorColor: AppColors.primary,
        dividerColor: Colors.transparent,
        labelStyle: TextStyle(
          fontFamily: baseFont,
          fontSize: 13,
          fontWeight: FontWeight.w900,
        ),
        unselectedLabelStyle: TextStyle(
          fontFamily: baseFont,
          fontSize: 13,
          fontWeight: FontWeight.w700,
        ),
      ),
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        elevation: 0,
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: AppColors.primary,
      ),
      dividerTheme: const DividerThemeData(
        color: AppColors.border,
        thickness: 1,
      ),
    );
  }
}
