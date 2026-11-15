import {
  Apartment,
  AuditLog,
  BackupJob,
  BillingPeriod,
  Donation,
  DonationCampaign,
  FeeExemption,
  FeeType,
  Household,
  Invoice,
  Payment,
  ProfileChangeRequest,
  Resident,
  TemporaryStay,
  User,
} from '../types';
import {
  INITIAL_APARTMENTS,
  INITIAL_AUDIT_LOGS,
  INITIAL_BACKUP_JOBS,
  INITIAL_BILLING_PERIODS,
  INITIAL_CHANGE_REQUESTS,
  INITIAL_DONATION_CAMPAIGNS,
  INITIAL_DONATIONS,
  INITIAL_EXPIRING_STAYS,
  INITIAL_FEE_EXEMPTIONS,
  INITIAL_FEE_TYPES,
  INITIAL_HOUSEHOLDS,
  INITIAL_INVOICES,
  INITIAL_PAYMENTS,
  INITIAL_RESIDENTS,
  INITIAL_USERS,
} from './mockData';

const STORAGE_PREFIX = 'bluemoon_';

function getStorage<T>(key: string, initial: T): T {
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + key);
    if (!raw) {
      localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(initial));
      return initial;
    }
    return JSON.parse(raw);
  } catch {
    return initial;
  }
}

function setStorage<T>(key: string, data: T): void {
  try {
    localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(data));
  } catch (err) {
    console.error('Failed to save to localStorage', err);
  }
}

export class ApiClient {
  private static token: string | null = localStorage.getItem('bluemoon_token');

  static setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('bluemoon_token', token);
    } else {
      localStorage.removeItem('bluemoon_token');
    }
  }

  static getToken(): string | null {
    return this.token;
  }

  // --- Real Fetch with Graceful Mock Fallback ---
  private static async request<T>(
    endpoint: string,
    options: RequestInit = {},
    mockFallback?: () => T
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(`/api/v1${endpoint}`, {
        ...options,
        headers,
      });

      if (!response.ok) {
        let errData;
        try {
          errData = await response.json();
        } catch {
          errData = { message: response.statusText };
        }

        // If backend actually answered with an API business error (e.g., 400, 423), throw it
        if (response.status !== 404 && response.status !== 502 && response.status !== 503) {
          throw new Error(errData.message || 'Lỗi hệ thống');
        }

        // If 404 or server down, fallback to mock if available
        if (mockFallback) return mockFallback();
        throw new Error(errData.message || 'Lỗi kết nối máy chủ');
      }

      return (await response.json()) as T;
    } catch (err: any) {
      // If network fetch fails (backend not running locally), seamlessly fallback
      if (mockFallback) {
        return mockFallback();
      }
      throw err;
    }
  }

  // ==========================================
  // AUTH (US-28, US-29, US-44)
  // ==========================================
  static async login(username: string, password: string): Promise<{ token: string; user: User }> {
    return this.request(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      },
      () => {
        const users = getStorage<User[]>('users', INITIAL_USERS);
        const user = users.find((u) => u.username.toLowerCase() === username.trim().toLowerCase());
        if (!user) {
          throw new Error('Tên đăng nhập hoặc mật khẩu không chính xác.');
        }

        if (password !== 'BlueMoon@2026') {
          throw new Error('Tên đăng nhập hoặc mật khẩu không chính xác.');
        }

        const token = `fake-jwt-${user.id}-${Date.now()}`;
        this.setToken(token);
        return { token, user };
      }
    );
  }

  static async changePassword(old_password: string, new_password: string): Promise<void> {
    return this.request(
      '/auth/change-password',
      {
        method: 'POST',
        body: JSON.stringify({ old_password, new_password }),
      },
      () => {
        if (new_password.length < 8) {
          throw new Error('Mật khẩu mới phải có tối thiểu 8 ký tự.');
        }
      }
    );
  }

  // ==========================================
  // APARTMENTS & HOUSEHOLDS (US-01, US-02, US-03)
  // ==========================================
  static async getApartments(): Promise<Apartment[]> {
    return this.request('/apartments', {}, () => getStorage('apartments', INITIAL_APARTMENTS));
  }

  static async addApartment(data: Partial<Apartment>): Promise<Apartment> {
    const apts = getStorage<Apartment[]>('apartments', INITIAL_APARTMENTS);
    const newApt: Apartment = {
      id: apts.length + 1,
      code: data.code || `B${1000 + apts.length}`,
      floor: data.floor || 1,
      area_m2: data.area_m2 || 70,
      status: 'ACTIVE',
      note: data.note,
      current_household: null,
    };
    apts.push(newApt);
    setStorage('apartments', apts);
    return newApt;
  }

  static async getHouseholds(): Promise<Household[]> {
    return this.request('/households', {}, () => getStorage('households', INITIAL_HOUSEHOLDS));
  }

  static async transferApartment(apartmentId: number, newHouseholdCode: string, ownerName: string, phone: string) {
    const households = getStorage<Household[]>('households', INITIAL_HOUSEHOLDS);
    const apartments = getStorage<Apartment[]>('apartments', INITIAL_APARTMENTS);
    const apt = apartments.find((a) => a.id === apartmentId);

    if (!apt) throw new Error('Không tìm thấy căn hộ');

    const newH: Household = {
      id: households.length + 1,
      household_code: newHouseholdCode,
      status: 'ACTIVE',
      contact_phone: phone,
      apartment: { id: apt.id, code: apt.code, floor: apt.floor, area_m2: apt.area_m2 },
      member_count: 1,
      credit_balance: 0,
      total_debt: 0,
      occupancy_start_date: new Date().toISOString().split('T')[0],
    };

    households.push(newH);
    setStorage('households', households);

    apt.current_household = {
      id: newH.id,
      household_code: newH.household_code,
      head_name: ownerName,
      contact_phone: phone,
      member_count: 1,
    };
    setStorage('apartments', apartments);
    return newH;
  }

  // ==========================================
  // RESIDENTS & STAYS (US-05..US-10)
  // ==========================================
  static async getResidents(): Promise<Resident[]> {
    return this.request('/residents', {}, () => getStorage('residents', INITIAL_RESIDENTS));
  }

  static async addResident(data: Partial<Resident>): Promise<Resident> {
    const residents = getStorage<Resident[]>('residents', INITIAL_RESIDENTS);
    const normalizedCCCD = data.cccd?.trim();

    // Kiểm tra CCCD trùng
    if (normalizedCCCD) {
      const duplicate = residents.find(
        (r) =>
          !r.is_deleted &&
          r.cccd?.trim() === normalizedCCCD
      );

      if (duplicate) {
        const households = getStorage<Household[]>(
          'households',
          INITIAL_HOUSEHOLDS
        );

        const household = households.find(
          (h) => h.id === duplicate.household_id
        );

        throw new Error(
          `CCCD đã tồn tại tại hộ ${household?.household_code ?? duplicate.household_id}, người sử dụng: ${duplicate.full_name}.`
        );
      }
    }

    const newR: Resident = {
      id: residents.length + 1,
      household_id: data.household_id || 1,
      full_name: data.full_name || '',
      date_of_birth: data.date_of_birth || '2000-01-01',
      gender: data.gender || 'NAM',
      cccd: normalizedCCCD || undefined,
      phone: data.phone,
      relationship_to_head: data.relationship_to_head || 'Thành viên',
      is_head: data.is_head || false,
      residence_status: 'THUONG_TRU',
    };
    residents.push(newR);
    setStorage('residents', residents);
    return newR;
  }

  static async getExpiringStays(): Promise<TemporaryStay[]> {
    return this.request('/temporary-stays/expiring', {}, () => getStorage('expiring_stays', INITIAL_EXPIRING_STAYS));
  }

  // ==========================================
  // FEE CATALOG & BILLING (US-12..US-17, US-47)
  // ==========================================
  static async getFeeTypes(): Promise<FeeType[]> {
    return this.request('/fee-types', {}, () => getStorage('fee_types', INITIAL_FEE_TYPES));
  }

  static async addFeeType(data: Partial<FeeType>): Promise<FeeType> {
    const feeTypes = getStorage<FeeType[]>('fee_types', INITIAL_FEE_TYPES);
    const newFee: FeeType = {
      id: feeTypes.length + 1,
      code: data.code || `FEE_${Date.now()}`,
      name: data.name || '',
      fee_group: data.fee_group || 'MANAGEMENT',
      calc_method: data.calc_method || 'PER_M2',
      unit_label: data.unit_label || 'm²',
      vehicle_type: data.vehicle_type,
      is_pass_through: data.is_pass_through || false,
      cycle: data.cycle || 'MONTHLY',
      due_day: data.due_day || 15,
      status: 'ACTIVE',
      description: data.description,
      current_unit_price: data.current_unit_price || 0,
    };
    feeTypes.push(newFee);
    setStorage('fee_types', feeTypes);
    return newFee;
  }

  static async deactivateFeeType(id: number): Promise<void> {
    const feeTypes = getStorage<FeeType[]>('fee_types', INITIAL_FEE_TYPES);
    const fee = feeTypes.find((f) => f.id === id);
    if (fee) {
      fee.status = 'INACTIVE';
      setStorage('fee_types', feeTypes);
    }
  }

  static async getBillingPeriods(): Promise<BillingPeriod[]> {
    return this.request('/billing-periods', {}, () => getStorage('billing_periods', INITIAL_BILLING_PERIODS));
  }

  static async generateBillingPeriod(periodMonth: string, name: string): Promise<BillingPeriod> {
    const periods = getStorage<BillingPeriod[]>('billing_periods', INITIAL_BILLING_PERIODS);
    const newP: BillingPeriod = {
      id: periods.length + 1,
      period_month: periodMonth,
      name: name,
      due_date: `${periodMonth.slice(0, 7)}-20`,
      status: 'OPEN',
      generated_at: new Date().toISOString(),
      total_invoices: 1000,
      total_receivable: 1460000000,
      total_collected: 0,
    };
    periods.unshift(newP);
    setStorage('billing_periods', periods);
    return newP;
  }

  static async getInvoices(): Promise<Invoice[]> {
    return this.request('/invoices', {}, () => getStorage('invoices', INITIAL_INVOICES));
  }

  // ==========================================
  // CASHIER & PAYMENTS (US-18, US-19, US-20, US-22)
  // ==========================================
  static async getPayments(): Promise<Payment[]> {
    return this.request('/payments', {}, () => getStorage('payments', INITIAL_PAYMENTS));
  }

  static async collectPayment(payload: {
    household_id: number;
    amount: number;
    method: 'CASH' | 'BANK_TRANSFER';
    reference_no?: string;
    item_ids: number[];
  }): Promise<Payment> {
    const payments = getStorage<Payment[]>('payments', INITIAL_PAYMENTS);
    const invoices = getStorage<Invoice[]>('invoices', INITIAL_INVOICES);
    const invoice = invoices.find((inv) => inv.household_id === payload.household_id);

    const receiptNo = `BL${String(payments.length + 1).padStart(8, '0')}`;
    const newPayment: Payment = {
      id: payments.length + 1,
      receipt_no: receiptNo,
      household_id: payload.household_id,
      household_code: invoice ? invoice.household_code : 'H-UNKNOWN',
      apartment_code: invoice ? invoice.apartment_code : '---',
      payer_name: invoice ? invoice.head_name : 'Cư dân',
      paid_at: new Date().toISOString(),
      amount: payload.amount,
      allocated_amount: payload.amount > (invoice?.remaining_amount || 0) ? (invoice?.remaining_amount || 0) : payload.amount,
      credit_amount: payload.amount > (invoice?.remaining_amount || 0) ? payload.amount - (invoice?.remaining_amount || 0) : 0,
      method: payload.method,
      reference_no: payload.reference_no,
      collected_by_name: 'Thủ quỹ trực quầy',
      status: 'VALID',
      print_count: 1,
      allocations: (invoice?.items || []).map((it) => ({
        id: it.id,
        invoice_item_id: it.id,
        fee_name: it.fee_name,
        amount: it.net_amount - it.paid_amount,
      })),
    };

    if (invoice) {
      invoice.paid_amount += newPayment.allocated_amount;
      invoice.remaining_amount = Math.max(0, invoice.total_due - invoice.paid_amount);
      if (invoice.remaining_amount === 0) {
        invoice.status = 'PAID';
      } else {
        invoice.status = 'PARTIAL';
      }
      setStorage('invoices', invoices);
    }

    payments.unshift(newPayment);
    setStorage('payments', payments);
    return newPayment;
  }

  static async cancelPayment(id: number, reason: string): Promise<void> {
    const payments = getStorage<Payment[]>('payments', INITIAL_PAYMENTS);
    const payment = payments.find((p) => p.id === id);
    if (!payment) throw new Error('Biên lai không tồn tại');

    payment.status = 'CANCELLED';
    payment.cancel_reason = reason;
    payment.cancelled_by_name = 'Lãnh đạo BQT / Kế toán trưởng';
    payment.cancelled_at = new Date().toISOString();
    setStorage('payments', payments);
  }

  static async recordPrintCount(paymentId: number): Promise<number> {
    const payments = getStorage<Payment[]>('payments', INITIAL_PAYMENTS);
    const payment = payments.find((p) => p.id === paymentId);
    if (payment) {
      payment.print_count += 1;
      setStorage('payments', payments);
      return payment.print_count;
    }
    return 1;
  }

  // ==========================================
  // DONATIONS (US-40, US-41, US-42)
  // ==========================================
  static async getDonationCampaigns(): Promise<DonationCampaign[]> {
    return this.request('/donations/campaigns', {}, () => getStorage('donation_campaigns', INITIAL_DONATION_CAMPAIGNS));
  }

  static async addDonation(data: {
    campaign_id: number;
    household_id: number;
    amount: number;
    donor_name: string;
    method: 'CASH' | 'BANK_TRANSFER';
  }): Promise<Donation> {
    const donations = getStorage<Donation[]>('donations', INITIAL_DONATIONS);
    const campaigns = getStorage<DonationCampaign[]>('donation_campaigns', INITIAL_DONATION_CAMPAIGNS);
    const camp = campaigns.find((c) => c.id === data.campaign_id);

    const voucherNo = `QT${String(donations.length + 1).padStart(8, '0')}`;
    const newDonation: Donation = {
      id: donations.length + 1,
      campaign_id: data.campaign_id,
      campaign_name: camp?.name || 'Quỹ tự nguyện',
      household_id: data.household_id,
      household_code: 'H-B1204-01',
      apartment_code: 'B1204',
      donor_name: data.donor_name,
      voucher_no: voucherNo,
      amount: data.amount,
      donated_at: new Date().toISOString(),
      method: data.method,
      status: 'VALID',
      collected_by_name: 'Thủ quỹ',
    };

    if (camp) {
      camp.total_raised += data.amount;
      camp.total_donors += 1;
      setStorage('donation_campaigns', campaigns);
    }

    donations.unshift(newDonation);
    setStorage('donations', donations);
    return newDonation;
  }

  // ==========================================
  // RESIDENT PORTAL & CHANGE REQUESTS (US-33..35)
  // ==========================================
  static async getChangeRequests(): Promise<ProfileChangeRequest[]> {
    return this.request('/change-requests', {}, () => getStorage('change_requests', INITIAL_CHANGE_REQUESTS));
  }

  static async submitChangeRequest(data: {
    request_type: 'UPDATE_RESIDENT' | 'ADD_RESIDENT' | 'UPDATE_HOUSEHOLD';
    proposed_data: Record<string, any>;
    evidence_files: string[];
  }): Promise<ProfileChangeRequest> {
    const requests = getStorage<ProfileChangeRequest[]>('change_requests', INITIAL_CHANGE_REQUESTS);
    const newReq: ProfileChangeRequest = {
      id: requests.length + 1,
      household_id: 1,
      household_code: 'H-B1204-01',
      apartment_code: 'B1204',
      requested_by_username: 'cudan_b1204',
      request_type: data.request_type,
      proposed_data: data.proposed_data,
      evidence_files: data.evidence_files,
      status: 'PENDING',
      created_at: new Date().toISOString(),
    };
    requests.unshift(newReq);
    setStorage('change_requests', requests);
    return newReq;
  }

  static async reviewChangeRequest(id: number, status: 'APPROVED' | 'REJECTED', reject_reason?: string): Promise<void> {
    const requests = getStorage<ProfileChangeRequest[]>('change_requests', INITIAL_CHANGE_REQUESTS);
    const req = requests.find((r) => r.id === id);
    if (!req) throw new Error('Yêu cầu không tồn tại');

    if (status === 'REJECTED' && !reject_reason) {
      throw new Error('Bắt buộc phải nhập lý do từ chối.');
    }

    req.status = status;
    req.reject_reason = reject_reason;
    req.reviewed_by_name = 'Trưởng BQT';
    req.reviewed_at = new Date().toISOString();
    setStorage('change_requests', requests);
  }

  // ==========================================
  // ADMIN SYSTEM, USERS & AUDIT LOGS (US-30..32, US-45)
  // ==========================================
  static async getUsers(): Promise<User[]> {
    return this.request('/users', {}, () => getStorage('users', INITIAL_USERS));
  }

  static async toggleUserStatus(userId: number): Promise<void> {
    const users = getStorage<User[]>('users', INITIAL_USERS);
    const user = users.find((u) => u.id === userId);
    if (user) {
      user.is_active = !user.is_active;
      setStorage('users', users);
    }
  }

  static async getAuditLogs(): Promise<AuditLog[]> {
    return this.request('/audit-logs', {}, () => getStorage('audit_logs', INITIAL_AUDIT_LOGS));
  }

  static async getBackupJobs(): Promise<BackupJob[]> {
    return this.request('/system/backups', {}, () => getStorage('backup_jobs', INITIAL_BACKUP_JOBS));
  }

  static async triggerBackup(): Promise<BackupJob> {
    const jobs = getStorage<BackupJob[]>('backup_jobs', INITIAL_BACKUP_JOBS);
    const newJob: BackupJob = {
      id: jobs.length + 1,
      status: 'SUCCEEDED',
      requested_by_name: 'Quản Trị Viên (Thao tác tay)',
      requested_at: new Date().toISOString(),
      finished_at: new Date().toISOString(),
      size_bytes: 48500000,
      file_path: `/backups/bluemoon_backup_manual_${Date.now()}.sql.gz`,
    };
    jobs.unshift(newJob);
    setStorage('backup_jobs', jobs);
    return newJob;
  }
}
