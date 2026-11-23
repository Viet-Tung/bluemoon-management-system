from datetime import date, datetime
import io
import re
from typing import Any, Dict, List, Optional  # [SỬA] Bỏ import thừa Set, Tuple
import openpyxl
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.rbac_middleware import AppAPIException
from app.core.security import generate_secure_temporary_password, get_password_hash
from app.models.property import Apartment, ApartmentOccupancy, Household, Resident
from app.models.user import AuditLog, Role, User
from app.schemas.import_data import ImportResult


def _calculate_age(dob: date) -> int:
    """Tính tuổi chính xác theo ngày sinh."""
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _parse_date(val: Any) -> Optional[date]:
    """Chuyển đổi linh hoạt giá trị ngày từ ô Excel (datetime, date, text)."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(val_str, fmt).date()
            except ValueError:
                continue
    return None


def _is_truthy(val: Any) -> bool:
    """Kiểm tra giá trị boolean biểu thị 'Có/Là chủ hộ'."""
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    val_str = str(val).strip().upper()
    return val_str in ("1", "TRUE", "CÓ", "CO", "YES", "X", "CHỦ HỘ", "CHU HO")


def _normalize_gender(val: Any) -> Optional[str]:
    """Chuẩn hóa giá trị giới tính sang NAM, NU, KHAC."""
    if val is None:
        return None
    val_str = str(val).strip().upper()
    if val_str in ("NAM", "MALE", "M"):
        return "NAM"
    if val_str in ("NU", "NỮ", "FEMALE", "F"):
        return "NU"
    if val_str in ("KHAC", "KHÁC", "OTHER"):
        return "KHAC"
    return None


def import_residents_excel(
    file_bytes: bytes,
    db: Session,
    current_user_id: int,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> ImportResult:
    """
    Xử lý import danh sách căn hộ, hộ gia đình và nhân khẩu hàng loạt từ file Excel (US-04).
    Quy tắc ACID: Có bất kỳ lỗi nào ở bất kỳ dòng nào -> rollback toàn bộ 100% và trả về lỗi 422 IMPORT_FAILED.
    """
    # 1. Đọc file Excel từ buffer
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    except Exception:
        raise AppAPIException(
            status_code=400,
            code="VALIDATION_ERROR",
            message="File tải lên không phải là file Excel (.xlsx) hợp lệ hoặc tệp đã bị hỏng.",
        )

    ws = wb.active
    if not ws or ws.max_row < 2:
        raise AppAPIException(
            status_code=400,
            code="VALIDATION_ERROR",
            message="File Excel rỗng hoặc không có dòng dữ liệu nào sau dòng tiêu đề.",
        )

    # 2. Ánh xạ cột tiêu đề (Dòng 1)
    header_row = [str(cell.value or "").strip().lower() for cell in ws[1]]

    col_map: Dict[str, Optional[int]] = {
        "apartment_code": None,
        "floor": None,
        "area_m2": None,
        "household_code": None,
        "contact_phone": None,
        "contact_email": None,
        "full_name": None,
        "date_of_birth": None,
        "gender": None,
        "cccd": None,
        "relationship_to_head": None,
        "is_head": None,
    }

    keywords = {
        "apartment_code": ["mã căn hộ", "mã căn", "apartment_code", "căn hộ"],
        "floor": ["tầng", "floor"],
        "area_m2": ["diện tích", "diện tích (m2)", "area_m2", "diện tích m2"],
        "household_code": ["mã hộ gia đình", "mã hộ", "household_code"],
        "contact_phone": ["sđt liên hệ", "sđt", "số điện thoại", "phone", "contact_phone"],
        "contact_email": ["email liên hệ", "email", "contact_email"],
        "full_name": ["họ và tên", "họ tên", "full_name", "tên nhân khẩu"],
        "date_of_birth": ["ngày sinh", "date_of_birth", "dob"],
        "gender": ["giới tính", "gender"],
        "cccd": ["số cccd", "cccd", "số cccd/cmnd", "cmnd"],
        "relationship_to_head": ["quan hệ với chủ hộ", "quan hệ", "relationship_to_head"],
        "is_head": ["là chủ hộ", "chủ hộ", "is_head"],
    }

    for idx, text in enumerate(header_row):
        for field, patterns in keywords.items():
            if col_map[field] is None:
                if any(p == text or p in text for p in patterns):
                    col_map[field] = idx
                    break

    required_cols = ["apartment_code", "floor", "area_m2", "household_code", "full_name", "date_of_birth", "gender"]
    missing_cols = [c for c in required_cols if col_map[c] is None]
    if missing_cols:
        raise AppAPIException(
            status_code=400,
            code="VALIDATION_ERROR",
            message=f"File Excel thiếu các cột bắt buộc: {', '.join(missing_cols)}.",
        )

    # 3. Quét từng dòng dữ liệu và kiểm tra hợp lệ
    errors: List[Dict[str, Any]] = []
    rows_data: List[Dict[str, Any]] = []

    file_cccds: Dict[str, int] = {}  # cccd -> row_idx
    file_households: Dict[str, Dict[str, Any]] = {}  # hcode -> {apt_code, phone, email, head_count, first_row}
    file_apartments: Dict[str, Dict[str, Any]] = {}  # apt_code -> {floor, area_m2, row}
    # [SỬA] Map kiểm tra 1 căn hộ không được gán cho 2 hộ gia đình khác nhau trong cùng file
    apt_to_household: Dict[str, Dict[str, Any]] = {}  # apt_code -> {household_code, row}

    def get_cell(row_cells, field_name: str) -> Any:
        c_idx = col_map.get(field_name)
        if c_idx is not None and c_idx < len(row_cells):
            return row_cells[c_idx].value
        return None

    total_rows = 0

    for r_idx in range(2, ws.max_row + 1):
        row_cells = ws[r_idx]

        # Kiểm tra nếu dòng hoàn toàn trống thì bỏ qua
        all_empty = all(c.value is None or str(c.value).strip() == "" for c in row_cells)
        if all_empty:
            continue

        total_rows += 1

        raw_apt_code = get_cell(row_cells, "apartment_code")
        raw_floor = get_cell(row_cells, "floor")
        raw_area = get_cell(row_cells, "area_m2")
        raw_hcode = get_cell(row_cells, "household_code")
        raw_phone = get_cell(row_cells, "contact_phone")
        raw_email = get_cell(row_cells, "contact_email")
        raw_name = get_cell(row_cells, "full_name")
        raw_dob = get_cell(row_cells, "date_of_birth")
        raw_gender = get_cell(row_cells, "gender")
        raw_cccd = get_cell(row_cells, "cccd")
        raw_rel = get_cell(row_cells, "relationship_to_head")
        raw_head = get_cell(row_cells, "is_head")

        # --- A. Kiểm tra Căn hộ ---
        apt_code = str(raw_apt_code).strip() if raw_apt_code is not None else ""
        if not apt_code:
            errors.append({"row": r_idx, "field": "apartment_code", "message": "Mã căn hộ không được để trống."})

        # [SỬA] Kiểm tra chặt số tầng: chặn số thập phân (vd 5.5) và giá trị boolean
        floor_val: Optional[int] = None
        try:
            if raw_floor is None or isinstance(raw_floor, bool):
                raise ValueError()
            floor_float = float(raw_floor)
            if not floor_float.is_integer():
                raise ValueError()
            floor_val = int(floor_float)
            if floor_val <= 0:
                errors.append({"row": r_idx, "field": "floor", "message": "Số tầng phải là số nguyên lớn hơn 0."})
        except (ValueError, TypeError):
            errors.append({"row": r_idx, "field": "floor", "message": "Số tầng phải là số nguyên hợp lệ."})

        area_val: Optional[float] = None
        try:
            if raw_area is None or isinstance(raw_area, bool):
                raise ValueError()
            area_val = float(raw_area)
            if area_val <= 0:
                errors.append({"row": r_idx, "field": "area_m2", "message": "Diện tích căn hộ phải là số dương lớn hơn 0."})
        except (ValueError, TypeError):
            errors.append({"row": r_idx, "field": "area_m2", "message": "Diện tích căn hộ không hợp lệ."})

        if apt_code and floor_val and floor_val > 0 and area_val and area_val > 0:
            if apt_code not in file_apartments:
                file_apartments[apt_code] = {"floor": floor_val, "area_m2": area_val, "row": r_idx}
            else:
                existing_apt = file_apartments[apt_code]
                if existing_apt["floor"] != floor_val or abs(existing_apt["area_m2"] - area_val) > 0.001:
                    errors.append({
                        "row": r_idx,
                        "field": "apartment_code",
                        "message": f"Thông tin tầng ({floor_val}) hoặc diện tích ({area_val}) của căn hộ '{apt_code}' không đồng nhất với dòng {existing_apt['row']}.",
                    })

        # --- B. Kiểm tra Hộ gia đình ---
        hcode = str(raw_hcode).strip() if raw_hcode is not None else ""
        if not hcode:
            errors.append({"row": r_idx, "field": "household_code", "message": "Mã hộ gia đình không được để trống."})

        phone_str = str(raw_phone).strip() if raw_phone is not None and str(raw_phone).strip() else None
        email_str = str(raw_email).strip() if raw_email is not None and str(raw_email).strip() else None
        if email_str and not re.match(r"[^@]+@[^@]+\.[^@]+", email_str):
            errors.append({"row": r_idx, "field": "contact_email", "message": f"Địa chỉ email '{email_str}' không hợp lệ."})

        # --- C. Kiểm tra Nhân khẩu ---
        name_str = str(raw_name).strip() if raw_name is not None else ""
        if not name_str:
            errors.append({"row": r_idx, "field": "full_name", "message": "Họ và tên nhân khẩu không được để trống."})

        dob_val = _parse_date(raw_dob)
        if not dob_val:
            errors.append({"row": r_idx, "field": "date_of_birth", "message": "Ngày sinh không đúng định dạng hợp lệ (YYYY-MM-DD hoặc DD/MM/YYYY)."})
        elif dob_val > date.today():
            errors.append({"row": r_idx, "field": "date_of_birth", "message": "Ngày sinh không được nằm ở tương lai."})

        gender_val = _normalize_gender(raw_gender)
        if not gender_val:
            errors.append({"row": r_idx, "field": "gender", "message": f"Giới tính '{raw_gender}' không hợp lệ (chỉ chấp nhận NAM, NU hoặc KHAC)."})

        is_head_val = _is_truthy(raw_head)
        rel_str = str(raw_rel).strip() if raw_rel is not None and str(raw_rel).strip() else ("CHỦ HỘ" if is_head_val else "THÀNH VIÊN")

        # Kiểm tra CCCD
        cccd_clean: Optional[str] = None
        if raw_cccd is not None:
            raw_c_str = str(raw_cccd).strip()
            if raw_c_str.endswith(".0"):
                raw_c_str = raw_c_str[:-2]
            if raw_c_str:
                cccd_clean = raw_c_str

        if dob_val and dob_val <= date.today():
            age = _calculate_age(dob_val)
            if age >= 14:
                if not cccd_clean:
                    errors.append({"row": r_idx, "field": "cccd", "message": "Nhân khẩu từ 14 tuổi trở lên bắt buộc phải có số CCCD/CMND."})
                elif not cccd_clean.isdigit() or len(cccd_clean) not in (9, 12):
                    errors.append({"row": r_idx, "field": "cccd", "message": f"Số CCCD/CMND '{cccd_clean}' không hợp lệ (phải gồm 9 hoặc 12 chữ số)."})
            else:
                if cccd_clean and (not cccd_clean.isdigit() or len(cccd_clean) not in (9, 12)):
                    errors.append({"row": r_idx, "field": "cccd", "message": f"Số CCCD/CMND '{cccd_clean}' không hợp lệ (phải gồm 9 hoặc 12 chữ số)."})

        if cccd_clean:
            if cccd_clean in file_cccds:
                errors.append({
                    "row": r_idx,
                    "field": "cccd",
                    "message": f"Số CCCD '{cccd_clean}' bị trùng lặp với dòng {file_cccds[cccd_clean]} trong file.",
                })
            else:
                file_cccds[cccd_clean] = r_idx

        # Gom nhóm hộ gia đình để kiểm tra chủ hộ và thông tin liên hệ
        if hcode:
            if hcode not in file_households:
                file_households[hcode] = {
                    "apartment_code": apt_code,
                    "phone": phone_str,
                    "email": email_str,
                    "head_count": 1 if is_head_val else 0,
                    "first_row": r_idx,
                }
            else:
                hh_group = file_households[hcode]
                if hh_group["apartment_code"] != apt_code:
                    errors.append({
                        "row": r_idx,
                        "field": "apartment_code",
                        "message": f"Hộ gia đình '{hcode}' cư trú ở căn '{hh_group['apartment_code']}' nhưng dòng này lại ghi căn '{apt_code}'.",
                    })
                # [SỬA] Bổ sung SĐT/Email nếu dòng đầu tiên của hộ để trống (ưu tiên thông tin của Chủ hộ)
                if phone_str and (not hh_group["phone"] or is_head_val):
                    hh_group["phone"] = phone_str
                if email_str and (not hh_group["email"] or is_head_val):
                    hh_group["email"] = email_str
                if is_head_val:
                    hh_group["head_count"] += 1

            # [SỬA] Chặn 2 hộ gia đình khác nhau ở chung 1 căn hộ trong cùng file Excel
            if apt_code:
                if apt_code not in apt_to_household:
                    apt_to_household[apt_code] = {"household_code": hcode, "row": r_idx}
                elif apt_to_household[apt_code]["household_code"] != hcode:
                    prev = apt_to_household[apt_code]
                    errors.append({
                        "row": r_idx,
                        "field": "apartment_code",
                        "message": f"Căn hộ '{apt_code}' đã được gán cho hộ '{prev['household_code']}' ở dòng {prev['row']}, không thể gán thêm cho hộ '{hcode}'.",
                    })

        rows_data.append({
            "row": r_idx,
            "apartment_code": apt_code,
            "floor": floor_val,
            "area_m2": area_val,
            "household_code": hcode,
            "contact_phone": phone_str,
            "contact_email": email_str,
            "full_name": name_str,
            "date_of_birth": dob_val,
            "gender": gender_val or "NAM",
            "cccd": cccd_clean,
            "relationship_to_head": rel_str,
            "is_head": is_head_val,
        })

    # [SỬA] Chặn trường hợp file chỉ có tiêu đề và các dòng trắng (total_rows == 0)
    if total_rows == 0:
        raise AppAPIException(
            status_code=400,
            code="VALIDATION_ERROR",
            message="File Excel không có dòng dữ liệu hợp lệ nào.",
        )

    # Kiểm tra mỗi hộ phải có đúng 1 chủ hộ
    for hcode, h_info in file_households.items():
        if h_info["head_count"] != 1:
            errors.append({
                "row": h_info["first_row"],
                "field": "is_head",
                "message": f"Hộ gia đình '{hcode}' phải có đúng 1 Chủ hộ (hiện có {h_info['head_count']} chủ hộ trong file).",
            })

    # --- D. Kiểm tra xung đột với CSDL hiện tại ---
    if file_apartments:
        apt_codes = list(file_apartments.keys())
        existing_apts = db.scalars(select(Apartment).where(Apartment.code.in_(apt_codes))).all()
        occupied_apt_ids = set()
        if existing_apts:
            occ_apt_ids = db.scalars(
                select(ApartmentOccupancy.apartment_id).where(
                    ApartmentOccupancy.apartment_id.in_([a.id for a in existing_apts]),
                    ApartmentOccupancy.end_date.is_(None),
                )
            ).all()
            occupied_apt_ids = set(occ_apt_ids)

        for apt in existing_apts:
            if apt.id in occupied_apt_ids:
                row_num = file_apartments[apt.code]["row"]
                errors.append({
                    "row": row_num,
                    "field": "apartment_code",
                    "message": f"Căn hộ '{apt.code}' đã tồn tại trên hệ thống và đang có người cư trú.",
                })

    if file_households:
        hh_codes = list(file_households.keys())
        existing_hhs = db.scalars(select(Household.household_code).where(Household.household_code.in_(hh_codes))).all()
        for ex_code in existing_hhs:
            row_num = file_households[ex_code]["first_row"]
            errors.append({
                "row": row_num,
                "field": "household_code",
                "message": f"Mã hộ gia đình '{ex_code}' đã tồn tại trên hệ thống.",
            })

    if file_cccds:
        existing_cccds = db.scalars(
            select(Resident.cccd).where(
                Resident.cccd.in_(list(file_cccds.keys())),
                Resident.is_deleted.is_(False),
            )
        ).all()
        for ex_cccd in existing_cccds:
            row_num = file_cccds[ex_cccd]
            errors.append({
                "row": row_num,
                "field": "cccd",
                "message": f"Số CCCD '{ex_cccd}' đã tồn tại trên hệ thống.",
            })

    # Nếu có bất kỳ lỗi nào -> Báo 422 IMPORT_FAILED và rollback 100%
    if errors:
        db.rollback()
        errors.sort(key=lambda x: x.get("row", 0))
        raise AppAPIException(
            status_code=422,
            code="IMPORT_FAILED",
            message=f"File import có {len(errors)} lỗi dữ liệu. Đã rollback toàn bộ.",
            details=errors,
        )

    # 4. GIAO DỊCH NGUYÊN TỬ (ACID): Commit toàn bộ dữ liệu vào DB
    try:
        # A. Tạo các căn hộ mới hoặc lấy căn hộ có sẵn chưa có người ở
        created_apartments: Dict[str, Apartment] = {}
        for apt_code, a_info in file_apartments.items():
            apt = db.scalar(select(Apartment).where(Apartment.code == apt_code))
            if not apt:
                apt = Apartment(
                    code=apt_code,
                    floor=a_info["floor"],
                    area_m2=a_info["area_m2"],
                    status="ACTIVE",
                    note="Import tự động từ file Excel",
                )
                db.add(apt)
                db.flush()
            created_apartments[apt_code] = apt

        # B. Lấy vai trò RESIDENT để sinh tài khoản
        resident_role = db.scalar(select(Role).where(Role.code == "RESIDENT"))
        if not resident_role:
            # [SỬA] Bỏ hardcode id=4 để DB tự sinh khóa chính
            resident_role = Role(code="RESIDENT", name="Cư dân")
            db.add(resident_role)
            db.flush()

        # C. Tạo từng Hộ gia đình và Lịch sử cư trú
        created_households: Dict[str, Household] = {}
        for hcode, h_info in file_households.items():
            apt = created_apartments[h_info["apartment_code"]]
            hh = Household(
                household_code=hcode,
                status="ACTIVE",
                contact_phone=h_info["phone"],
                contact_email=h_info["email"],
                note="Import tự động từ file Excel",
            )
            db.add(hh)
            db.flush()
            created_households[hcode] = hh

            # Tạo lịch sử cư trú
            occ = ApartmentOccupancy(
                apartment_id=apt.id,
                household_id=hh.id,
                start_date=date.today(),
            )
            db.add(occ)

            # Tự động sinh tài khoản cư dân mặc định (D-12, AC-30.2)
            clean_code = re.sub(r"[^a-zA-Z0-9_.-]", "_", hcode.lower())
            base_user = f"res_{clean_code}"
            uname = base_user
            cnt = 1
            while db.scalar(select(User).where(func.lower(User.username) == uname.lower())):
                uname = f"{base_user}_{cnt}"
                cnt += 1

            temp_pwd = generate_secure_temporary_password(12)
            hashed_pwd = get_password_hash(temp_pwd)

            res_user = User(
                username=uname,
                password_hash=hashed_pwd,
                full_name=f"Đại diện {hcode}",
                email=h_info["email"],
                phone=h_info["phone"],
                role_id=resident_role.id,
                household_id=hh.id,
                is_active=True,
                must_change_password=True,
                failed_login_count=0,
            )
            db.add(res_user)

        # D. Tạo từng Nhân khẩu
        for r_item in rows_data:
            hh = created_households[r_item["household_code"]]
            res_obj = Resident(
                household_id=hh.id,
                full_name=r_item["full_name"],
                date_of_birth=r_item["date_of_birth"],
                gender=r_item["gender"],
                cccd=r_item["cccd"],
                relationship_to_head=r_item["relationship_to_head"],
                is_head=r_item["is_head"],
                residence_status="THUONG_TRU",
                status_effective_date=date.today(),
                is_deleted=False,
            )
            db.add(res_obj)

        db.flush()

        # E. Ghi Audit Log (US-32)
        audit = AuditLog(
            user_id=current_user_id,
            action="IMPORT_EXCEL",
            entity_type="SYSTEM",
            entity_id=str(current_user_id),
            old_value=None,
            new_value={
                "total_rows": total_rows,
                "imported_rows": len(rows_data),
                "apartments_count": len(file_apartments),
                "households_count": len(file_households),
            },
            reason=f"Import thành công {len(rows_data)} nhân khẩu ({len(file_households)} hộ, {len(file_apartments)} căn hộ) từ Excel.",
            ip_address=client_ip,
            user_agent=user_agent,
        )
        db.add(audit)
        db.commit()

        return ImportResult(total_rows=total_rows, imported_rows=len(rows_data))

    except Exception as e:
        db.rollback()
        if isinstance(e, AppAPIException):
            raise e
        raise AppAPIException(
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            message=f"Đã xảy ra lỗi trong quá trình lưu dữ liệu import: {str(e)}",
        )