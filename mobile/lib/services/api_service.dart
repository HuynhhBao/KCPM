import 'dart:async';

import 'package:shared_preferences/shared_preferences.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';

class ApiService {
  static const String apiHost = String.fromEnvironment(
    'API_HOST',
    defaultValue: '192.168.0.5',
  );

  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: '',
  );

  static String get baseUrl {
    if (apiBaseUrl.isNotEmpty) {
      return apiBaseUrl;
    }

    if (kIsWeb) {
      return kReleaseMode
          ? 'https://chungvi-production.up.railway.app/api'
          : 'http://127.0.0.1:8000/api';
    }

    return 'https://chungvi-production.up.railway.app/api';
  }

  static final Dio dio = Dio(
    BaseOptions(
      baseUrl: baseUrl,
      connectTimeout:
          const Duration(seconds: 15),
      receiveTimeout:
          const Duration(seconds: 15),
      sendTimeout:
          const Duration(seconds: 15),
      headers: {
        'Content-Type':
            'application/json',
      },
    ),
  );

  static Future<bool>? _refreshTokenFuture;

  static Future<bool> _refreshTokenSafely() async {
    _refreshTokenFuture ??= refreshAccessToken();

    try {
      return await _refreshTokenFuture!;
    } finally {
      _refreshTokenFuture = null;
    }
  }

  static Future<void> saveTokens({
    required String access,
    required String refresh,
    String? email,
  }) async {
    final prefs = await SharedPreferences.getInstance();

    await prefs.setString('access_token', access);
    await prefs.setString('refresh_token', refresh);

    if (email != null) {
      await prefs.setString('user_email', email);
    }

    dio.options.headers['Authorization'] = 'Bearer $access';
  }

  static Future<String?> getAccessToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }

  static Future<String?> getRefreshToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('refresh_token');
  }

  static Future<String?> getSavedEmail() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('user_email');
  }

  static Future<void> init() async {
    await loadToken();

    dio.interceptors.clear();

    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (
          options,
          handler,
        ) async {
          final access =
              await getAccessToken();

          if (access != null &&
              access.isNotEmpty) {
            options.headers[
                    'Authorization'] =
                'Bearer $access';
          }

          return handler.next(
            options,
          );
        },
        onError: (
          error,
          handler,
        ) async {
          final statusCode =
              error.response
                  ?.statusCode;

          final requestOptions =
              error.requestOptions;

          final isAuthApi =
              requestOptions.path
                      .contains(
                    '/auth/login/',
                  ) ||
                  requestOptions.path
                      .contains(
                    '/auth/register/',
                  ) ||
                  requestOptions.path
                      .contains(
                    '/auth/refresh/',
                  );

          final alreadyRetried =
              requestOptions.extra['alreadyRetried'] ==
                  true;

          if (
            statusCode == 401 &&
            !isAuthApi &&
            !alreadyRetried
          ) {
            final refreshed =
                await _refreshTokenSafely();

            if (refreshed) {
              try {
                final access =
                    await getAccessToken();

                final retryResponse =
                    await dio.fetch<
                        dynamic>(
                  requestOptions
                      .copyWith(
                    headers: {
                      ...requestOptions
                          .headers,
                      if (access !=
                          null)
                        'Authorization':
                            'Bearer $access',
                    },
                    extra: {
                      ...requestOptions
                          .extra,
                      'alreadyRetried':
                          true,
                    },
                  ),
                );

                return handler.resolve(
                  retryResponse,
                );
              } catch (_) {
                return handler.next(error);
              }
            } else {
              await logout();
            }
          }

          return handler.reject(
            DioException(
              requestOptions:
                  requestOptions,
              response:
                  error.response,
              type: error.type,
              error:
                  parseDioException(
                error,
              ),
            ),
          );
        },
      ),
    );
  }

  static Future<void> loadToken() async {
    final access = await getAccessToken();

    if (access != null && access.isNotEmpty) {
      dio.options.headers['Authorization'] = 'Bearer $access';
    }
  }

  static Future<bool> refreshAccessToken() async {
    try {
      final refresh = await getRefreshToken();

      if (refresh == null || refresh.isEmpty) {
        return false;
      }

      final refreshDio = Dio(
        BaseOptions(
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 10),
          sendTimeout: const Duration(seconds: 10),
          headers: {
            'Content-Type': 'application/json',
          },
        ),
      );

      final response = await refreshDio.post(
        '$baseUrl/auth/refresh/',
        data: {
          'refresh': refresh,
        },
      );

      final newAccess = response.data['access'];

      if (newAccess == null || newAccess.toString().isEmpty) {
        return false;
      }

      final prefs = await SharedPreferences.getInstance();

      await prefs.setString('access_token', newAccess);

      dio.options.headers['Authorization'] = 'Bearer $newAccess';

      return true;
    } catch (_) {
      return false;
    }
  }

  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();

    await prefs.remove('access_token');
    await prefs.remove('refresh_token');
    await prefs.remove('user_email');

    dio.options.headers.remove('Authorization');
  }

  static Future<bool> checkAuth() async {
    final access = await getAccessToken();

    if (access == null || access.isEmpty) {
      return false;
    }

    try {
      await dio.get('/households/');
      return true;
    } catch (_) {
      final refreshed = await _refreshTokenSafely();

      if (refreshed) {
        try {
          await dio.get('/households/');
          return true;
        } catch (_) {}
      }

      await logout();
      return false;
    }
  }

  static Future<Response> login({
    required String email,
    required String password,
  }) async {
    return dio.post(
      '/auth/login/',
      data: {
        'email': email,
        'password': password,
      },
    );
  }

  static Future<Response> register({
    required String email,
    required String username,
    required String password,
  }) async {
    return dio.post(
      '/auth/register/',
      data: {
        'email': email,
        'username': username,
        'password': password,
      },
    );
  }

  static Future<Response> verifyRegisterOTP({
    required String email,
    required String otp,
  }) async {
    return dio.post(
      '/auth/verify-register-otp/',
      data: {
        'email': email,
        'otp': otp,
      },
    );
  }

  static Future<Response> resendRegisterOTP({
    required String email,
  }) async {
    return dio.post(
      '/auth/resend-register-otp/',
      data: {
        'email': email,
      },
    );
  }

  static Future<Response> forgotPassword({
    required String email,
  }) async {
    return dio.post(
      '/auth/forgot-password/',
      data: {
        'email': email,
      },
    );
  }

  static Future<Response> resetPassword({
    required String email,
    required String otp,
    required String newPassword,
    required String confirmPassword,
  }) async {
    return dio.post(
      '/auth/reset-password/',
      data: {
        'email': email,
        'otp': otp,
        'new_password': newPassword,
        'confirm_password': confirmPassword,
      },
    );
  }

  static Future<Response> changePassword({
    required String oldPassword,
    required String newPassword,
    required String confirmPassword,
  }) async {
    return dio.post(
      '/auth/change-password/',
      data: {
        'old_password': oldPassword,
        'new_password': newPassword,
        'confirm_password': confirmPassword,
      },
    );
  }

  static Future<List<dynamic>> getHouseholds() async {
      final response = await dio.get('/households/');
      return List<dynamic>.from(response.data);
    }

  static Future<List<dynamic>> getHouseholdSummaries() async {
    final response = await dio.get('/households/summary/');
    return List<dynamic>.from(response.data);
  }
  
  static Future<Response> createHousehold({
    required String name,
    String? description,
  }) async {
    return dio.post(
      '/households/',
      data: {
        'name': name,
        'description': description ?? '',
      },
    );
  }

  static Future<void> leaveHousehold(String householdId) async {
    await dio.post('/households/$householdId/leave/');
  }

  static Future<void> deleteHousehold(String householdId) async {
    try {
      await dio.delete('/households/$householdId/');
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể xóa nhóm';
    }
  }

  static Future<Map<String, dynamic>>
    getHouseholdDetail(
    String householdId,
  ) async {
    try {
      final response = await dio.get(
        '/households/$householdId/',
      );

      return Map<String, dynamic>.from(
        response.data,
      );
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể tải chi tiết nhóm';
    }
  }

  static Future<Map<String, dynamic>>addMemberToHousehold({
    required String householdId,
    required String email,
    String role = 'member',
  }) async {
    try {
      final response = await dio.post(
        '/households/$householdId/members/add/',
        data: {
          'email': email,
          'role': role,
        },
      );

      return Map<String, dynamic>.from(
        response.data,
      );
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể thêm thành viên';
    }
  }

  static Future<Map<String, dynamic>> kickMemberFromHousehold({
  required String householdId,
  required String memberId,
}) async {
  try {
    final response = await dio.delete(
      '/households/$householdId/members/$memberId/kick/',
    );

    return Map<String, dynamic>.from(
      response.data,
    );
  } on DioException catch (e) {
    throw parseDioException(e);
  } catch (_) {
    throw 'Không thể xóa thành viên khỏi nhóm';
  }
}

  static Future<Map<String, dynamic>> getAllActivities({
    int page = 1,
  }) async {
    final response = await dio.get(
      '/households/activities/?page=$page',
    );

    return {
      'results': List<dynamic>.from(
        response.data['results'],
      ),
      'next': response.data['next'],
    };
  }

  static Future<Map<String, dynamic>> getActivities(
    String householdId, {
    int page = 1,
  }) async {
    final response = await dio.get(
      '/households/$householdId/activities/?page=$page',
    );

    return {
      'results': List<dynamic>.from(
        response.data['results'],
      ),
      'next': response.data['next'],
    };
  }

  static Future<Map<String, dynamic>> getHouseholdExpenses(
    String householdId, {
    int page = 1,
  }) async {
    final response = await dio.get(
      '/expenses/household/$householdId/?page=$page',
    );

    return {
      'results': List<dynamic>.from(
        response.data['results'],
      ),
      'next': response.data['next'],
    };
  }

  static Future<Map<String, dynamic>> getHouseholdDebts(
    String householdId, {
    int page = 1,
  }) async {
    try {
      final response = await dio.get(
        '/expenses/household/$householdId/debts/?page=$page',
      );

      final data = response.data;

      if (data is List) {
        return {
          'results': List<dynamic>.from(data),
          'next': null,
        };
      }

      if (data is Map) {
        return {
          'results': List<dynamic>.from(
            data['results'] ?? [],
          ),
          'next': data['next'],
        };
      }

      return {
        'results': <dynamic>[],
        'next': null,
      };
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể tải danh sách công nợ';
    }
  }

  static Future<List<dynamic>> getAllDebtsFromHouseholds(
    List<String> householdIds,
  ) async {
    final List<dynamic> allDebts = [];

    for (final id in householdIds) {
      try {
        final response = await dio.get(
          '/expenses/household/$id/debts/',
        );

        if (response.data is List) {
          allDebts.addAll(response.data);
        }
      } catch (_) {}
    }

    return allDebts;
  }

  static Future<Map<String, dynamic>> createExpense({
    required String householdId,
    required String title,
    required double amount,
    required String expenseDate,
    required List<int> participants,
    String note = '',
  }) async {
    try {
      final response = await dio.post(
        '/expenses/',
        data: {
          'household': householdId,
          'title': title,
          'amount': amount.toInt(),
          'expense_date': expenseDate,
          'participants': participants
              .map(
                (userId) => {
                  'user_id': userId,
                },
              )
              .toList(),
          'note': note,
          'split_type': 'equal',
        },
      );

      return Map<String, dynamic>.from(
        response.data,
      );
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể tạo khoản chi';
    }
  }

  static Future<Map<String, dynamic>> getExpenseDetail(
    String expenseId,
  ) async {
    try {
      final response = await dio.get(
        '/expenses/$expenseId/',
      );

      return Map<String, dynamic>.from(
        response.data,
      );
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể tải khoản chi';
    }
  }

  static Future<Map<String, dynamic>> updateExpense({
    required String expenseId,
    required String title,
    required double amount,
    required String expenseDate,
    required List<int> participants,
    String note = '',
  }) async {
    try {
      final response = await dio.patch(
        '/expenses/$expenseId/',
        data: {
          'title': title,
          'amount': amount.toInt(),
          'expense_date': expenseDate,
          'participants': participants
              .map(
                (userId) => {
                  'user_id': userId,
                },
              )
              .toList(),
          'note': note,
          'split_type': 'equal',
        },
      );

      return Map<String, dynamic>.from(
        response.data,
      );
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể cập nhật khoản chi';
    }
  }

  static Future<void> deleteExpense(
    String expenseId,
  ) async {
    try {
      await dio.delete(
        '/expenses/$expenseId/',
      );
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể xóa khoản chi';
    }
  }

  static Future<void> saveFCMToken(
    String token,
  ) async {
    await dio.post(
      '/notifications/save-fcm-token/',
      data: {
        'token': token,
        'device_type': 'android',
      },
    );
  }

  static Future<Map<String, dynamic>> getNotifications({
    int page = 1,
  }) async {
    final response = await dio.get(
      '/notifications/?page=$page',
    );

    return {
      'results': List<dynamic>.from(
        response.data['results'],
      ),
      'next': response.data['next'],
    };
  }

  static Future<int> getUnreadNotificationCount() async {
    final response = await dio.get('/notifications/unread-count/');
    return response.data['unread_count'] ?? 0;
  }

  static Future<void> markNotificationAsRead(
    String notificationId,
  ) async {
    await dio.patch(
      '/notifications/$notificationId/read/',
    );
  }

  static Future<void> markAllNotificationsAsRead() async {
    await dio.patch('/notifications/mark-all-read/');
  }

  static Future<Map<String, dynamic>> getProfile() async {
    final response = await dio.get('/auth/profile/');
    return Map<String, dynamic>.from(response.data);
  }

  static Future<Map<String, dynamic>> updateProfile({
    required String fullName,
    required String phoneNumber,
    required String bankName,
    required String bankAccountNumber,
    required String bankAccountHolder,
  }) async {
    try {
      final response = await dio.patch(
        '/auth/profile/',
        data: {
          'full_name': fullName,
          'phone_number': phoneNumber,
          'bank_name': bankName,
          'bank_account_number': bankAccountNumber,
          'bank_account_holder': bankAccountHolder,
        },
      );

      return Map<String, dynamic>.from(response.data);
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể cập nhật hồ sơ';
    }
  }

  static Future<Map<String, dynamic>> updateAvatar({
    required List<int> bytes,
    required String fileName,
  }) async {
    try {
      final formData = FormData.fromMap({
        'avatar': MultipartFile.fromBytes(
          bytes,
          filename: fileName,
        ),
      });

      final response = await dio.patch(
        '/auth/profile/',
        data: formData,
        options: Options(
          contentType: 'multipart/form-data',
        ),
      );

      return Map<String, dynamic>.from(response.data);
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể cập nhật ảnh đại diện';
    }
  }

  static Future<void> loginWithGoogle() async {
    final GoogleSignIn googleSignIn =
        GoogleSignIn(
      scopes: [
        'email',
      ],
    );
    
    await googleSignIn.signOut();

    final GoogleSignInAccount?
        googleUser =
        await googleSignIn.signIn();

    if (googleUser == null) {
      throw Exception(
        'Người dùng đã huỷ đăng nhập',
      );
    }

    final GoogleSignInAuthentication
        googleAuth =
        await googleUser.authentication;

    String? token =
        googleAuth.idToken;

    token ??=
        googleAuth.accessToken;

    if (token == null) {
      throw Exception(
        'Không lấy được Google token',
      );
    }

    final response = await dio.post(
      '/auth/google-login/',
      data: {
        'token': token,
      },
    );

    final access =
        response.data['access'];

    final refresh =
        response.data['refresh'];

    final email =
        response.data['user']['email'];

    await saveTokens(
      access: access,
      refresh: refresh,
      email: email,
    );
  }

  static Future<Map<String, dynamic>> createPairPayment({
    required String householdId,
    required int receiverId,
    required int amount,
    String note = '',
  }) async {
    try {
      final response = await dio.post(
        '/payments/households/$householdId/pair-payments/',
        data: {
          'receiver_id': receiverId,
          'amount': amount,
          'note': note,
        },
      );

      return Map<String, dynamic>.from(response.data);
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể gửi yêu cầu thanh toán';
    }
  }

  static Future<Map<String, dynamic>> markDebtPaid(
    String debtId, {
    String note = '',
  }) async {
    try {
      final response = await dio.post(
        '/payments/debts/$debtId/mark-paid/',
        data: {
          'note': note,
        },
      );

      return Map<String, dynamic>.from(
        response.data,
      );
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể gửi yêu cầu thanh toán';
    }
  }

  static Future<Map<String, dynamic>> confirmPayment(
    String paymentId, {
    String note = '',
  }) async {
    try {
      final response = await dio.post(
        '/payments/$paymentId/confirm/',
        data: {
          'note': note,
        },
      );

      return Map<String, dynamic>.from(
        response.data,
      );
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể xác nhận thanh toán';
    }
  }

  static Future<Map<String, dynamic>> rejectPayment(
    String paymentId, {
    String note = '',
  }) async {
    try {
      final response = await dio.post(
        '/payments/$paymentId/reject/',
        data: {
          'note': note,
        },
      );

      return Map<String, dynamic>.from(
        response.data,
      );
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể từ chối thanh toán';
    }
  }

  static Future<Map<String, dynamic>> getPendingPayments({
    int page = 1,
  }) async {
    try {
      final response = await dio.get(
        '/payments/pending/?page=$page',
      );

      final data = response.data;

      if (data is List) {
        return {
          'results': List<dynamic>.from(data),
          'next': null,
        };
      }

      if (data is Map) {
        return {
          'results': List<dynamic>.from(
            data['results'] ?? [],
          ),
          'next': data['next'],
        };
      }

      return {
        'results': <dynamic>[],
        'next': null,
      };
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể tải yêu cầu thanh toán';
    }
  }

  static String _extractErrorMessage(dynamic data) {
    if (data == null) {
      return '';
    }

    if (data is String) {
      return data;
    }

    if (data is Map) {
      final priorityKeys = [
        'detail',
        'message',
        'error',
        'non_field_errors',
      ];

      for (final key in priorityKeys) {
        final value = data[key];

        if (value == null) continue;

        if (value is List && value.isNotEmpty) {
          return value.first.toString();
        }

        if (value is String && value.trim().isNotEmpty) {
          return value;
        }
      }

      for (final entry in data.entries) {
        final value = entry.value;

        if (value is List && value.isNotEmpty) {
          return value.first.toString();
        }

        if (value is String && value.trim().isNotEmpty) {
          return value;
        }
      }
    }

    return '';
  }

  static String parseDioException(
    DioException error,
  ) {
    if (
      error.type ==
              DioExceptionType
                  .connectionTimeout ||
          error.type ==
              DioExceptionType
                  .receiveTimeout ||
          error.type ==
              DioExceptionType
                  .sendTimeout
    ) {
      return 'Kết nối quá chậm. Vui lòng thử lại.';
    }

    if (error.type ==
        DioExceptionType
            .connectionError) {
      return 'Không có kết nối mạng.';
    }

    final serverMessage = _extractErrorMessage(
      error.response?.data,
    );

    if (serverMessage.isNotEmpty) {
      return serverMessage;
    }

    final statusCode =
        error.response?.statusCode;

    if (statusCode == 400) {
      return 'Dữ liệu gửi lên không hợp lệ.';
    }

    if (statusCode == 401) {
      return 'Phiên đăng nhập đã hết hạn.';
    }

    if (statusCode == 403) {
      return 'Bạn không có quyền thực hiện thao tác này.';
    }

    if (statusCode == 404) {
      return 'Không tìm thấy dữ liệu.';
    }

    if (statusCode == 500) {
      return 'Máy chủ đang gặp sự cố.';
    }

    return 'Đã có lỗi xảy ra.';
  }

  static Future<Map<String, dynamic>>
      joinHousehold({
    required String inviteCode,
  }) async {
    try {
      final response = await dio.post(
        '/households/join/',
        data: {
          'invite_code': inviteCode,
        },
      );

      return Map<String, dynamic>.from(
        response.data,
      );
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể tham gia nhóm';
    }
  }

  static Future<Map<String, dynamic>> createVirtualHouseholdMember(
    String householdId, {
    required String displayName,
    String note = '',
  }) async {
    try {
      final response = await dio.post(
        '/households/$householdId/members/virtual/',
        data: {
          'display_name': displayName,
          'note': note,
        },
      );

      return Map<String, dynamic>.from(response.data);
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể tạo thành viên ảo';
    }
  }

  static Future<Map<String, dynamic>> createVirtualMember({
    required String householdId,
    required String displayName,
    String note = '',
  }) async {
    return createVirtualHouseholdMember(
      householdId,
      displayName: displayName,
      note: note,
    );
  }

  static Future<Map<String, dynamic>> getHouseholdMyDebtSummary(
    String householdId,
  ) async {
    try {
      final response = await dio.get(
        '/households/$householdId/my-debts/',
      );

      return Map<String, dynamic>.from(response.data);
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể tải tổng quan công nợ';
    }
  }

  static Future<Map<String, dynamic>> getHouseholdMyDebtDetail({
    required String householdId,
    required int otherUserId,
  }) async {
    try {
      final response = await dio.get(
        '/households/$householdId/my-debts/$otherUserId/',
      );

      return Map<String, dynamic>.from(response.data);
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể tải chi tiết công nợ';
    }
  }

  static Future<Map<String, dynamic>> getVirtualMemberDebts({
    required String householdId,
    required int virtualUserId,
  }) async {
    try {
      final response = await dio.get(
        '/households/$householdId/virtual-members/$virtualUserId/debts/',
      );

      return Map<String, dynamic>.from(response.data);
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể tải công nợ thành viên ảo';
    }
  }

  static Future<Map<String, dynamic>> getVirtualMemberDebtDetail({
    required String householdId,
    required int virtualUserId,
    required int otherUserId,
  }) async {
    try {
      final response = await dio.get(
        '/households/$householdId/virtual-members/$virtualUserId/debts/$otherUserId/',
      );

      return Map<String, dynamic>.from(response.data);
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể tải chi tiết công nợ thành viên ảo';
    }
  }

  static Future<Map<String, dynamic>> settleVirtualMemberDebtPair({
    required String householdId,
    required int virtualUserId,
    required int otherUserId,
  }) async {
    try {
      final response = await dio.post(
        '/households/$householdId/virtual-members/$virtualUserId/debts/$otherUserId/settle/',
      );

      return Map<String, dynamic>.from(response.data);
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể đánh dấu xử lý công nợ';
    }
  }

  static Future<Map<String, dynamic>> recordVirtualReceipt({
    required String householdId,
    required int virtualUserId,
    required int amount,
    String note = '',
  }) async {
    try {
      final response = await dio.post(
        '/payments/households/$householdId/virtual-receipts/',
        data: {
          'virtual_user_id': virtualUserId,
          'amount': amount,
          'note': note,
        },
      );

      return Map<String, dynamic>.from(response.data);
    } on DioException catch (e) {
      throw parseDioException(e);
    } catch (_) {
      throw 'Không thể ghi nhận tiền đã nhận';
    }
  }
}