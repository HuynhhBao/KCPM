import sys
import os
import subprocess
import json
import re

# BẢNG ÁNH XẠ CHUẨN TOÀN HỆ THỐNG KIỂM THỬ HỘP TRẮNG CHUNG VÍ (ĐỒNG BỘ SỐ NHIỀU)
MAPPING = {
    # === ACCOUNTS SERVICE (whitebox_tests/accounts) ===
    "001": ("accounts/views.py", "consume_cached_otp", None, "accounts"),
    "002": ("accounts/views.py", "request_google_json", None, "accounts"),
    "003": ("accounts/views.py", "get_google_identity", None, "accounts"),
    "004": ("accounts/views.py", "create", "RegisterView", "accounts"),
    "005": ("accounts/views.py", "post", "VerifyRegisterOTPView", "accounts"),
    "006": ("accounts/views.py", "post", "ResendRegisterOTPView", "accounts"),
    "007": ("accounts/serializers.py", "validate", "CustomTokenObtainPairSerializer", "accounts"),
    "008": ("accounts/views.py", "get", "UserAvatarView", "accounts"),
    "009": ("accounts/views.py", "post", "SaveFCMTokenView", "accounts"),
    "010": ("accounts/views.py", "post", "ChangePasswordView", "accounts"),
    "011": ("accounts/views.py", "post", "ForgotPasswordRequestView", "accounts"),
    "012": ("accounts/views.py", "post", "ResetPasswordView", "accounts"),
    "013": ("accounts/views.py", "post", "GoogleLoginView", "accounts"),
    "014": ("accounts/serializers.py", "validate_password_strength", None, "accounts"),
    "015": ("accounts/serializers.py", "normalize_phone_number", None, "accounts"),
    "016": ("accounts/serializers.py", "validate", "RegisterSerializer", "accounts"),
    "017": ("accounts/serializers.py", "validate_full_name", "UserProfileSerializer", "accounts"),
    "018": ("accounts/serializers.py", "validate_bank_account_number", "UserProfileSerializer", "accounts"),
    "019": ("accounts/serializers.py", "validate_avatar", "UserProfileSerializer", "accounts"),
    "020": ("accounts/serializers.py", "validate", "UserProfileSerializer", "accounts"),
    "021": ("accounts/serializers.py", "update", "UserProfileSerializer", "accounts"),
    "022": ("accounts/serializers.py", "validate", "ChangePasswordSerializer", "accounts"),
    "023": ("accounts/serializers.py", "validate", "ResetPasswordSerializer", "accounts"),
    "024": ("accounts/avatar_utils.py", "build_user_avatar_url", None, "accounts"),
    "025": ("accounts/cloudinary_storage.py", "configure_cloudinary", None, "accounts"),
    "026": ("accounts/cloudinary_storage.py", "normalize_avatar_image", None, "accounts"),
    "027": ("accounts/cloudinary_storage.py", "upload_user_avatar", None, "accounts"),
    "028": ("accounts/cloudinary_storage.py", "delete_cloudinary_avatar_safely", None, "accounts"),

    # === HOUSEHOLDS SERVICE (whitebox_tests/households) ===
    "029": ("households/views.py", "get_user_display_name", None, "households"),
    "030": ("households/views.py", "debt_remaining_to_int", None, "households"),
    "031": ("households/views.py", "debt_pending_amount_to_int", None, "households"),
    "032": ("households/views.py", "get_debt_item_status", None, "households"),
    "033": ("households/views.py", "serialize_debt_detail_item", None, "households"),
    "034": ("households/views.py", "serialize_debt_user", None, "households"),
    "035": ("households/views.py", "serialize_debt_payer", None, "households"),
    "036": ("households/views.py", "get_owner_household_or_response", None, "households"),
    "037": ("households/views.py", "get_virtual_pair_household_or_response", None, "households"),
    "038": ("households/views.py", "get_virtual_user_or_response", None, "households"),
    "039": ("households/views.py", "destroy", "HouseholdDetailView", "households"),
    "040": ("households/views.py", "post", "JoinHouseholdView", "households"),
    "041": ("households/views.py", "post", "AddHouseholdMemberView", "households"),
    "042": ("households/views.py", "post", "CreateVirtualHouseholdMemberView", "households"),
    "043": ("households/views.py", "delete", "KickHouseholdMemberView", "households"),
    "044": ("households/views.py", "post", "LeaveHouseholdView", "households"),
    "045": ("households/views.py", "get", "MyDebtSummaryView", "households"),
    "046": ("households/views.py", "get", "MyDebtDetailView", "households"),
    "047": ("households/views.py", "get", "VirtualMemberDebtSummaryView", "households"),
    "048": ("households/views.py", "get", "VirtualMemberDebtDetailView", "households"),
    "049": ("households/views.py", "post", "SettleVirtualMemberDebtPairView", "households"),
    "050": ("households/serializers.py", "validate_name", "HouseholdSerializer", "households"),
    "051": ("households/serializers.py", "validate_display_name", "CreateVirtualMemberSerializer", "households"),
    "052": ("households/serializers.py", "_get_user_debt_totals", "HouseholdSummarySerializer", "households"),
    "053": ("households/serializers.py", "get_user_avatar", "HouseholdMemberSerializer", "households"),
    "054": ("households/serializers.py", "get_actor_name", "ActivitySerializer", "households"),
    "106": ("households/views.py", "money_to_int", None, "households"),
    "107": ("households/views.py", "serialize_bank_info", None, "households"),
    "109": ("households/serializers.py", "get_avatar_url", "HouseholdSerializer", "households"),
    "110": ("households/serializers.py", "get_avatar_url", "HouseholdSummarySerializer", "households"),
    "111": ("households/serializers.py", "get_latest_activity", "HouseholdSummarySerializer", "households"),

    # === EXPENSES SERVICE (whitebox_tests/expenses) ===
    "055": ("expenses/serializers.py", "get_user_display_name", None, "expenses"),
    "056": ("expenses/serializers.py", "__init__", "ExpenseCreateUpdateSerializer", "expenses"),
    "057": ("expenses/serializers.py", "validate_title", "ExpenseCreateUpdateSerializer", "expenses"),
    "058": ("expenses/serializers.py", "validate_amount", "ExpenseCreateUpdateSerializer", "expenses"),
    "059": ("expenses/serializers.py", "validate_expense_date", "ExpenseCreateUpdateSerializer", "expenses"),
    "060": ("expenses/serializers.py", "validate", "ExpenseCreateUpdateSerializer", "expenses"),
    "061": ("expenses/serializers.py", "_build_split_items", "ExpenseCreateUpdateSerializer", "expenses"),
    "062": ("expenses/serializers.py", "_sync_participants_and_debts", "ExpenseCreateUpdateSerializer", "expenses"),
    "063": ("expenses/serializers.py", "get_payer_avatar", "ExpenseListSerializer", "expenses"),
    "064": ("expenses/serializers.py", "get_can_manage", "ExpenseListSerializer", "expenses"),
    "065": ("expenses/serializers.py", "get_pending_payment", "DebtSerializer", "expenses"),
    "066": ("expenses/serializers.py", "get_pending_payment_id", "DebtSerializer", "expenses"),
    "067": ("expenses/serializers.py", "get_pending_payment_status", "DebtSerializer", "expenses"),
    "068": ("expenses/serializers.py", "get_can_mark_paid", "DebtSerializer", "expenses"),
    "069": ("expenses/serializers.py", "get_can_confirm_payment", "DebtSerializer", "expenses"),
    "070": ("expenses/serializers.py", "get_from_user_avatar", "DebtSerializer", "expenses"),
    "071": ("expenses/serializers.py", "get_to_user_avatar", "DebtSerializer", "expenses"),
    "072": ("expenses/serializers.py", "get_user_avatar", "ExpenseParticipantSerializer", "expenses"),
    "073": ("expenses/views.py", "get_queryset", "ExpenseListView", "expenses"),
    "074": ("expenses/views.py", "get_serializer_class", "ExpenseDetailView", "expenses"),
    "075": ("expenses/views.py", "destroy", "ExpenseDetailView", "expenses"),
    "076": ("expenses/views.py", "get_queryset", "DebtListView", "expenses"),
    "077": ("expenses/models.py", "remaining_amount", "Debt", "expenses"),
    "078": ("expenses/models.py", "apply_payment", "Debt", "expenses"),
    "108": ("expenses/serializers.py", "get_has_virtual_member", "DebtSerializer", "expenses"),

    # === NOTIFICATIONS SERVICE (whitebox_tests/notifications) ===
    "079": ("notifications/firebase_service.py", "initialize_firebase", None, "notifications"),
    "080": ("notifications/firebase_service.py", "send_push_notification_to_user", None, "notifications"),
    "081": ("notifications/services.py", "create_notification", None, "notifications"),
    "082": ("notifications/serializers.py", "get_household_name", "NotificationSerializer", "notifications"),
    "083": ("notifications/views.py", "post", "SaveFCMTokenView", "notifications"),
    "084": ("notifications/views.py", "patch", "NotificationMarkReadView", "notifications"),

    # === PAYMENTS SERVICE (whitebox_tests/payments) ===
    "085": ("payments/views.py", "get_user_display_name", None, "payments"),
    "086": ("payments/views.py", "debt_remaining_amount", None, "payments"),
    "087": ("payments/views.py", "get_pending_amount_for_debt", None, "payments"),
    "088": ("payments/views.py", "get_debt_payable_amount", None, "payments"),
    "089": ("payments/views.py", "get_forward_debts_queryset", None, "payments"),
    "090": ("payments/views.py", "build_allocations_for_payment_mode", None, "payments"),
    "091": ("payments/views.py", "get_pair_debt_state", None, "payments"),
    "092": ("payments/views.py", "apply_pair_payment_to_debts", None, "payments"),
    "093": ("payments/views.py", "post", "MarkDebtPaidView", "payments"),
    "094": ("payments/views.py", "post", "CreatePairPaymentView", "payments"),
    "095": ("payments/views.py", "post", "RecordVirtualReceiptView", "payments"),
    "096": ("payments/views.py", "post", "ConfirmPaymentView", "payments"),
    "097": ("payments/views.py", "post", "RejectPaymentView", "payments"),
    "098": ("payments/serializers.py", "validate", "PairPaymentCreateSerializer", "payments"),
    "099": ("payments/serializers.py", "validate", "VirtualReceiptCreateSerializer", "payments"),
    "100": ("payments/serializers.py", "get_expense_id", "PaymentAllocationSerializer", "payments"),
    "101": ("payments/serializers.py", "get_expense_title", "PaymentAllocationSerializer", "payments"),
    "102": ("payments/serializers.py", "get_debt_id", "PaymentSerializer", "payments"),
    "103": ("payments/serializers.py", "get_expense_id", "PaymentSerializer", "payments"),
    "104": ("payments/serializers.py", "get_expense_title", "PaymentSerializer", "payments"),
    "105": ("payments/views.py", "debt_has_virtual_member", None, "payments"),
}

BASE_TEST_DIR = "whitebox_tests"
SERVICES = ["accounts", "households", "expenses", "notifications", "payments"]

def find_line_range(file_path, target_func, container_name):
    if not os.path.exists(file_path): return 1, 1
    with open(file_path, "r", encoding="utf-8") as f: lines = f.readlines()
    start_idx = None
    if container_name:
        container_idx = next((i for i, l in enumerate(lines) if re.match(r"^\s*class\s+" + container_name + r"\b", l)), None)
        if container_idx is None: return 1, len(lines)
        for idx in range(container_idx + 1, len(lines)):
            if lines[idx].strip() and not lines[idx].startswith(" ") and not lines[idx].startswith("\t") and not lines[idx].strip().startswith("#"): break
            if re.search(r"\bdef\s+" + target_func + r"\b", lines[idx]):
                start_idx = idx
                break
    else:
        start_idx = next((i for i, l in enumerate(lines) if re.search(r"^\s*def\s+" + target_func + r"\b", l)), None)
        
    if start_idx is None: return 1, len(lines)
    actual_start_idx = start_idx
    while actual_start_idx > 0 and lines[actual_start_idx - 1].strip().startswith("@"): actual_start_idx -= 1
    start_line = actual_start_idx + 1
    indent_match = re.match(r"^(\s*)", lines[start_idx])
    base_indent = len(indent_match.group(1)) if indent_match else 0
    end_line = len(lines)
    for idx in range(start_idx + 1, len(lines)):
        if lines[idx].strip() and not lines[idx].strip().startswith("#"):
            if len(re.match(r"^(\s*)", lines[idx]).group(1)) <= base_indent:
                end_line = idx
                break
    return start_line, end_line

def extract_test_cases(test_file_path):
    with open(test_file_path, "r", encoding="utf-8") as f: content = f.read()
    return re.findall(r"\bdef\s+(test_\w+)\b", content)

def get_coverage_for_cmd(cmd, target_file, func_lines):
    cov_app = target_file.split('/')[0]
    cmd_with_cov = f"{cmd} --cov={cov_app} --cov-report=json"
    subprocess.run(cmd_with_cov, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists("coverage.json"): return 0
    with open("coverage.json", "r", encoding="utf-8") as f: cov_report = json.load(f)
    file_key = next((k for k in cov_report["files"] if target_file in k.replace("\\", "/")), None)
    if file_key:
        f_data = cov_report["files"][file_key]
        executed = [l for l in f_data["executed_lines"] if l in func_lines]
        missing = [l for l in f_data["missing_lines"] if l in func_lines]
        total = len(executed) + len(missing)
        return (len(executed) / total * 100) if total > 0 else 100
    return 0

def process_wb(wb_num, test_file, service_folder):
    if wb_num not in MAPPING: return
    target_file, target_func, container_name, _ = MAPPING[wb_num]
    start_line, end_line = find_line_range(target_file, target_func, container_name)
    func_lines = list(range(start_line, end_line + 1))
    test_file_path = f"{BASE_TEST_DIR}/{service_folder}/{test_file}"
    
    total_cmd = f"pytest {test_file_path}"
    total_cover = get_coverage_for_cmd(total_cmd, target_file, func_lines)
    
    print("═"*75)
    print(f"🤖 [AUTOMATION BREAKDOWN LOG] - MÃ SỐ CA KIỂM THỬ: WB_{wb_num}")
    print(f"🎯 Hàm mục tiêu:  {container_name + '.' if container_name else ''}{target_func}() ➔ {target_file}")
    print(f"📍 Tọa độ dòng:  Từ dòng {start_line} đến dòng {end_line}")
    print(f"📊 ĐỘ PHỦ TỔNG THỂ CỦA HÀM KHI CHẠY GỘP: {total_cover:.0f}%")
    print("📋 CHI TIẾT ĐỘ PHỦ RIÊNG BIỆT CỦA TỪNG TEST CASE (TC):")
    
    test_cases = extract_test_cases(test_file_path)
    for tc in test_cases:
        isolated_cmd = f"pytest {test_file_path}::{tc}"
        tc_cover = get_coverage_for_cmd(isolated_cmd, target_file, func_lines)
        status_icon = "🟩" if tc_cover > 0 else "⬜"
        print(f"   ├── {status_icon} {tc}() ➔ Đóng góp độ phủ: {tc_cover:.0f}%")

def run_service_folder(service):
    service_path = f"{BASE_TEST_DIR}/{service}"
    if not os.path.exists(service_path):
        print(f"⚠️ Thư mục '{service_path}' không tồn tại.")
        return
    
    # Sử dụng Regex để quét tất cả các file có chứa từ khóa 'wb' hoặc 'WB' đi liền chữ số mà không phụ thuộc tiền tố
    all_files = os.listdir(service_path)
    test_files = []
    for f in all_files:
        if f.endswith(".py"):
            match = re.search(r"wb_?(\d{3})", f, re.IGNORECASE)
            if match:
                test_files.append((match.group(1), f))
                
    # Sắp xếp danh sách kiểm thử tuần tự theo số thứ tự tăng dần
    test_files.sort(key=lambda x: int(x[0]))
    
    for wb_num, tf in test_files:
        process_wb(wb_num, tf, service)

# =========================================================================
# LUỒNG ĐIỀU PHỐI THỰC THI CHÍNH (MAIN ROUTER)
# =========================================================================
if len(sys.argv) < 2:
    print("❌ Sai cú pháp! Hướng dẫn điều phối đa năng:")
    print("👉 Chạy 1 file test theo mã:      python run_wb.py 001")
    print("👉 Chạy 1 thư mục của service:    python run_wb.py accounts")
    print("👉 Chạy tất cả mọi service:       python run_wb.py all")
    sys.exit(1)

arg = sys.argv[1].lower()

if arg == "all":
    print(f"🚀 [Global Automation] Bắt đầu quét phân rã TOÀN BỘ {len(SERVICES)} dịch vụ...")
    for s in SERVICES:
        print(f"\n⚡ ĐANG THỰC THI KIỂM THỬ HỘP TRẮNG CHO SERVICE: [{s.upper()}]")
        run_service_folder(s)
    print("\n🏁 [FINISH ALL] Hoàn tất toàn bộ chu kỳ đo đạc hộp trắng hệ thống!")

elif arg in SERVICES:
    print(f"🚀 [Service Automation] Thực thi toàn bộ thư mục {BASE_TEST_DIR}/{arg}...")
    run_service_folder(arg)
    print(f"\n🏁 [FINISH SERVICE] Hoàn tất đo đạc thư mục [{arg.upper()}]!")

else:
    padded_num = arg.zfill(3)
    if padded_num in MAPPING:
        _, _, _, service_folder = MAPPING[padded_num]
        service_path = f"{BASE_TEST_DIR}/{service_folder}"
        
        if not os.path.exists(service_path):
            print(f"❌ Thư mục '{service_path}' không tồn tại. Vui lòng kiểm tra lại cấu trúc thư mục.")
            sys.exit(1)
            
        # Áp dụng cơ chế tìm kiếm tệp bằng Regex động bóc tách số thay vì so khớp chuỗi cố định
        test_file = next((f for f in os.listdir(service_path) if re.search(rf"wb_?{padded_num}", f, re.IGNORECASE) and f.endswith(".py")), None)
        if test_file:
            process_wb(padded_num, test_file, service_folder)
        else:
            print(f"❌ Không tìm thấy file test chứa mã wb{padded_num} trong thư mục {service_path}")
    else:
        print(f"❌ Mã số định danh WB_{padded_num} không tồn tại trong bảng ánh xạ hệ thống.")