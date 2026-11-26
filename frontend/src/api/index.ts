import {
  Apartment,
  AuditLog,
  BackupJob,
  BillingPeriod,
  DiscountType,
  FeeExemption,
  FeeRate,
  FeeType,
  GenerateResult,
  Household,
  HouseholdCreated,
  ImportResult,
  Invoice,
  InvoiceDetail,
  Page,
  Resident,
  Role,
  SearchResult,
  User,
  UserWithTempPassword,
  UtilityReading,
  Vehicle,
  VehicleType,
} from '../types';

export class ApiError extends Error {
  code: string;
  status: number;
  details: any[];

  constructor(code: string, message: string, status: number = 400, details: any[] = []) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export class ApiClient {
  private static token: string | null = localStorage.getItem('bluemoon_token');
  private static onUnauthorized: (() => void) | null = null;

  static setOnUnauthorized(cb: (() => void) | null) {
    this.onUnauthorized = cb;
  }

  static async fetchAllPages<T>(
    fetcher: (page: number, pageSize: number) => Promise<{ items: T[]; total: number }>,
    pageSize: number = 100,
    maxPages: number = 50
  ): Promise<T[]> {
    const first = await fetcher(1, pageSize);
    const items = [...(first.items || [])];
    const total = first.total ?? items.length;
    const totalPages = Math.min(Math.ceil(total / pageSize), maxPages);
    for (let page = 2; page <= totalPages; page++) {
      const next = await fetcher(page, pageSize);
      if (!next.items || next.items.length === 0) break;
      items.push(...next.items);
    }
    return items;
  }

  static setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('bluemoon_token', token);
    } else {
      localStorage.removeItem('bluemoon_token');
    }
  }

  static getToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem('bluemoon_token');
    }
    return this.token;
  }

  /**
   * Core request method communicating with backend FastAPI server.
   * Includes 8-second timeout via AbortController to avoid frozen UI.
   */
  private static async request<T>(
    endpoint: string,
    options: RequestInit = {},
    timeoutMs: number = 8000
  ): Promise<T> {
    const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
    const headers: Record<string, string> = {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...(options.headers as Record<string, string>),
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(`/api/v1${endpoint}`, {
        ...options,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errData: { code?: string; message?: string; details?: any[] } = {};
        try {
          errData = await response.json();
        } catch {
          errData = {
            code: response.status === 401 ? 'UNAUTHENTICATED' : 'HTTP_ERROR',
            message: response.statusText || 'Lỗi xử lý từ máy chủ',
          };
        }

        if (response.status === 401 && !endpoint.startsWith('/auth/login')) {
          this.setToken(null);
          this.onUnauthorized?.();
        }

        throw new ApiError(
          errData.code || 'HTTP_ERROR',
          errData.message || 'Lỗi xử lý từ hệ thống',
          response.status,
          errData.details || []
        );
      }

      if (response.status === 204) {
        return undefined as unknown as T;
      }

      return (await response.json()) as T;
    } catch (err: any) {
      clearTimeout(timeoutId);

      if (err instanceof ApiError) {
        throw err;
      }

      if (err.name === 'AbortError') {
        throw new ApiError(
          'REQUEST_TIMEOUT',
          'Yêu cầu kết nối quá thời gian chờ (8s). Máy chủ không phản hồi.',
          408
        );
      }

      // Failed to fetch: API service is offline
      throw new ApiError(
        'BACKEND_OFFLINE',
        'Không thể kết nối đến máy chủ hệ thống. Vui lòng kiểm tra kết nối hoặc dịch vụ máy chủ.',
        503
      );
    }
  }

  // ==========================================
  // AUTH (US-28, US-29, US-44)
  // ==========================================

  static async login(username: string, password: string): Promise<{ token: string; user: User }> {
    const res = await this.request<{
      token: string;
      token_type: string;
      expires_in: number;
      user: User;
    }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });

    this.setToken(res.token);
    return { token: res.token, user: res.user };
  }

  static async logout(): Promise<void> {
    try {
      await this.request<void>('/auth/logout', { method: 'POST' });
    } finally {
      this.setToken(null);
    }
  }

  static async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  static async changePassword(old_password: string, new_password: string): Promise<void> {
    return this.request<void>('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ old_password, new_password }),
    });
  }

  // ==========================================
  // ROLES & USERS (US-30, US-31)
  // ==========================================

  static async getRoles(): Promise<Role[]> {
    return this.request<Role[]>('/roles');
  }

  static async getUsers(params?: {
    page?: number;
    page_size?: number;
    q?: string;
    role?: string;
    is_active?: boolean;
  }): Promise<Page<User>> {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    if (params?.q) query.append('q', params.q);
    if (params?.role) query.append('role', params.role);
    if (params?.is_active !== undefined) query.append('is_active', String(params.is_active));

    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<Page<User>>(`/users${qs}`);
  }

  static async getUser(id: number): Promise<User> {
    return this.request<User>(`/users/${id}`);
  }

  static async createUser(payload: {
    username: string;
    full_name: string;
    role_id: number;
    email?: string;
    phone?: string;
  }): Promise<UserWithTempPassword> {
    return this.request<UserWithTempPassword>('/users', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  static async updateUser(
    id: number,
    payload: { full_name?: string; email?: string; phone?: string; is_active?: boolean }
  ): Promise<User> {
    return this.request<User>(`/users/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  static async setUserRole(userId: number, roleId: number): Promise<User> {
    return this.request<User>(`/users/${userId}/role`, {
      method: 'PUT',
      body: JSON.stringify({ role_id: roleId }),
    });
  }

  static async lockUser(userId: number): Promise<User> {
    return this.request<User>(`/users/${userId}/lock`, {
      method: 'POST',
    });
  }

  static async unlockUser(userId: number): Promise<User> {
    return this.request<User>(`/users/${userId}/unlock`, {
      method: 'POST',
    });
  }

  static async resetUserPassword(userId: number): Promise<{ temporary_password: string }> {
    return this.request<{ temporary_password: string }>(`/users/${userId}/reset-password`, {
      method: 'POST',
    });
  }

  // ==========================================
  // APARTMENTS (US-01)
  // ==========================================

  static async getApartments(params?: {
    page?: number;
    page_size?: number;
    floor?: number;
    status?: string;
  }): Promise<Page<Apartment>> {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    if (params?.floor !== undefined) query.append('floor', String(params.floor));
    if (params?.status) query.append('status', params.status);

    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<Page<Apartment>>(`/apartments${qs}`);
  }

  static async getApartment(id: number): Promise<Apartment> {
    return this.request<Apartment>(`/apartments/${id}`);
  }

  static async createApartment(payload: {
    code: string;
    floor: number;
    area_m2: number;
    note?: string;
  }): Promise<Apartment> {
    return this.request<Apartment>('/apartments', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  static async updateApartment(
    id: number,
    payload: { floor?: number; area_m2?: number; status?: string; note?: string }
  ): Promise<Apartment> {
    return this.request<Apartment>(`/apartments/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  // ==========================================
  // HOUSEHOLDS (US-01, US-02, US-03)
  // ==========================================

  static async getHouseholds(params?: {
    page?: number;
    page_size?: number;
    q?: string;
    status?: string;
  }): Promise<Page<Household>> {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    if (params?.q) query.append('q', params.q);
    if (params?.status) query.append('status', params.status);

    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<Page<Household>>(`/households${qs}`);
  }

  static async getHousehold(id: number): Promise<Household> {
    return this.request<Household>(`/households/${id}`);
  }

  static async createHousehold(payload: {
    household_code: string;
    apartment_id?: number;
    occupancy_start_date?: string;
    contact_phone?: string;
    contact_email?: string;
    note?: string;
    head?: {
      full_name: string;
      date_of_birth: string;
      gender: string;
      cccd?: string;
      phone?: string;
      email?: string;
      relationship_to_head?: string;
      is_head?: boolean;
    };
  }): Promise<HouseholdCreated> {
    return this.request<HouseholdCreated>('/households', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  static async updateHousehold(
    id: number,
    payload: { contact_phone?: string; contact_email?: string; note?: string }
  ): Promise<Household> {
    return this.request<Household>(`/households/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  static async deactivateHousehold(id: number, reason: string): Promise<Household> {
    return this.request<Household>(`/households/${id}/deactivate`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  static async transferApartment(
    id: number,
    payload: { new_household_id: number; effective_date: string; reason?: string }
  ): Promise<Household> {
    return this.request<Household>(`/households/${id}/transfer`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  static async changeHead(
    id: number,
    payload: { new_head_resident_id: number; effective_date: string; reason?: string }
  ): Promise<Household> {
    return this.request<Household>(`/households/${id}/head`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  // ==========================================
  // FEE TYPES (US-12, US-13)
  // ==========================================

  static async getFeeTypes(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    fee_group?: string;
  }): Promise<Page<FeeType>> {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    if (params?.status) query.append('status', params.status);
    if (params?.fee_group) query.append('fee_group', params.fee_group);

    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<Page<FeeType>>(`/fee-types${qs}`);
  }

  static async createFeeType(payload: {
    code: string;
    name: string;
    fee_group: string;
    calc_method: string;
    unit_label: string;
    vehicle_type?: string;
    is_pass_through?: boolean;
    provider_id?: number;
    cycle?: string;
    due_day?: number;
    description?: string;
  }): Promise<FeeType> {
    return this.request<FeeType>('/fee-types', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  static async updateFeeType(
    id: number,
    payload: {
      name?: string;
      unit_label?: string;
      cycle?: string;
      due_day?: number;
      description?: string;
    }
  ): Promise<FeeType> {
    return this.request<FeeType>(`/fee-types/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  static async deactivateFeeType(id: number): Promise<FeeType> {
    return this.request<FeeType>(`/fee-types/${id}/deactivate`, {
      method: 'POST',
    });
  }

  static async getFeeType(id: number): Promise<FeeType> {
    return this.request<FeeType>(`/fee-types/${id}`);
  }

  static async getFeeRates(feeTypeId: number): Promise<FeeRate[]> {
    return this.request<FeeRate[]>(`/fee-types/${feeTypeId}/rates`);
  }

  static async createFeeRate(
    feeTypeId: number,
    payload: { unit_price: number; effective_from: string }
  ): Promise<FeeRate> {
    return this.request<FeeRate>(`/fee-types/${feeTypeId}/rates`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // ==========================================
  // FEE EXEMPTIONS (US-15, US-16)
  // ==========================================

  static async getFeeExemptions(params?: {
    page?: number;
    page_size?: number;
    household_id?: number;
    fee_type_id?: number;
    status?: string;
  }): Promise<Page<FeeExemption>> {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    if (params?.household_id) query.append('household_id', String(params.household_id));
    if (params?.fee_type_id) query.append('fee_type_id', String(params.fee_type_id));
    if (params?.status) query.append('status', params.status);

    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<Page<FeeExemption>>(`/fee-exemptions${qs}`);
  }

  static async createFeeExemption(payload: {
    household_id: number;
    fee_type_id: number;
    discount_type: DiscountType;
    discount_value: number;
    reason: string;
    decision_no?: string;
    valid_from: string;
    valid_to?: string;
  }): Promise<FeeExemption> {
    return this.request<FeeExemption>('/fee-exemptions', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  static async revokeFeeExemption(id: number): Promise<FeeExemption> {
    return this.request<FeeExemption>(`/fee-exemptions/${id}/revoke`, {
      method: 'POST',
    });
  }

  // ==========================================
  // RESIDENTS (US-05, US-06)
  // ==========================================

  static async getHouseholdResidents(
    householdId: number,
    params?: {
      page?: number;
      page_size?: number;
      residence_status?: string;
      include_deleted?: boolean;
    }
  ): Promise<Page<Resident>> {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    if (params?.residence_status) query.append('residence_status', params.residence_status);
    if (params?.include_deleted !== undefined) {
      query.append('include_deleted', String(params.include_deleted));
    }

    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<Page<Resident>>(`/households/${householdId}/residents${qs}`);
  }

  static async createResident(
    householdId: number,
    payload: {
      full_name: string;
      date_of_birth: string;
      gender: string;
      cccd?: string;
      phone?: string;
      email?: string;
      relationship_to_head?: string;
      is_head?: boolean;
    }
  ): Promise<Resident> {
    return this.request<Resident>(`/households/${householdId}/residents`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  static async getResident(residentId: number): Promise<Resident> {
    return this.request<Resident>(`/residents/${residentId}`);
  }

  static async updateResident(
    residentId: number,
    payload: {
      full_name?: string;
      date_of_birth?: string;
      gender?: string;
      cccd?: string;
      phone?: string;
      email?: string;
      relationship_to_head?: string;
    }
  ): Promise<Resident> {
    return this.request<Resident>(`/residents/${residentId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  static async deleteResident(residentId: number, reason?: string): Promise<void> {
    const qs = reason ? `?reason=${encodeURIComponent(reason)}` : '';
    return this.request<void>(`/residents/${residentId}${qs}`, {
      method: 'DELETE',
    });
  }

  // ==========================================
  // IMPORT EXCEL (US-04)
  // ==========================================

  static async importExcel(file: File): Promise<ImportResult> {
    const formData = new FormData();
    formData.append('file', file);
    return this.request<ImportResult>(
      '/import/excel',
      {
        method: 'POST',
        body: formData,
      },
      30000
    );
  }

  // ==========================================
  // VEHICLES (US-36)
  // ==========================================

  static async getVehicles(params?: {
    page?: number;
    page_size?: number;
    household_id?: number;
    plate_number?: string;
    vehicle_type?: string;
    status?: string;
  }): Promise<Page<Vehicle>> {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    if (params?.household_id) query.append('household_id', String(params.household_id));
    if (params?.plate_number) query.append('plate_number', params.plate_number);
    if (params?.vehicle_type) query.append('vehicle_type', params.vehicle_type);
    if (params?.status) query.append('status', params.status);

    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<Page<Vehicle>>(`/vehicles${qs}`);
  }

  static async createVehicle(payload: {
    household_id: number;
    plate_number: string;
    vehicle_type: VehicleType;
    brand?: string;
    color?: string;
    registered_date?: string;
  }): Promise<Vehicle> {
    return this.request<Vehicle>('/vehicles', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  static async updateVehicle(
    id: number,
    payload: {
      plate_number?: string;
      vehicle_type?: VehicleType;
      brand?: string;
      color?: string;
    }
  ): Promise<Vehicle> {
    return this.request<Vehicle>(`/vehicles/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  static async unregisterVehicle(
    id: number,
    payload?: { unregistered_date?: string }
  ): Promise<Vehicle> {
    return this.request<Vehicle>(`/vehicles/${id}/unregister`, {
      method: 'POST',
      body: payload ? JSON.stringify(payload) : undefined,
    });
  }

  // ==========================================
  // BILLING, UTILITY READINGS & INVOICES (US-17, US-37, US-38, US-47)
  // ==========================================

  static async getBillingPeriods(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    year?: number;
  }): Promise<Page<BillingPeriod>> {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    if (params?.status) query.append('status', params.status);
    if (params?.year) query.append('year', String(params.year));

    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<Page<BillingPeriod>>(`/billing-periods${qs}`);
  }

  static async createBillingPeriod(payload: {
    period_month: string;
    name: string;
    due_date?: string;
  }): Promise<BillingPeriod> {
    return this.request<BillingPeriod>('/billing-periods', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  static async getBillingPeriod(id: number): Promise<BillingPeriod> {
    return this.request<BillingPeriod>(`/billing-periods/${id}`);
  }

  static async generateBillingInvoices(id: number): Promise<GenerateResult> {
    return this.request<GenerateResult>(
      `/billing-periods/${id}/generate`,
      {
        method: 'POST',
      },
      30000
    );
  }

  static async closeBillingPeriod(id: number): Promise<BillingPeriod> {
    return this.request<BillingPeriod>(`/billing-periods/${id}/close`, {
      method: 'POST',
    });
  }

  static async getInvoices(params?: {
    page?: number;
    page_size?: number;
    billing_period_id?: number;
    household_id?: number;
    status?: string;
  }): Promise<Page<Invoice>> {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    if (params?.billing_period_id) query.append('billing_period_id', String(params.billing_period_id));
    if (params?.household_id) query.append('household_id', String(params.household_id));
    if (params?.status) query.append('status', params.status);

    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<Page<Invoice>>(`/invoices${qs}`);
  }

  static async getInvoice(id: number): Promise<InvoiceDetail> {
    return this.request<InvoiceDetail>(`/invoices/${id}`);
  }

  static async getUtilityReadings(params?: {
    page?: number;
    page_size?: number;
    billing_period_id?: number;
    fee_type_id?: number;
    household_id?: number;
  }): Promise<Page<UtilityReading>> {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    if (params?.billing_period_id) query.append('billing_period_id', String(params.billing_period_id));
    if (params?.fee_type_id) query.append('fee_type_id', String(params.fee_type_id));
    if (params?.household_id) query.append('household_id', String(params.household_id));

    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<Page<UtilityReading>>(`/utility-readings${qs}`);
  }

  static async createUtilityReading(payload: {
    household_id: number;
    fee_type_id: number;
    billing_period_id: number;
    previous_index: number;
    current_index: number;
    unit_price?: number;
  }): Promise<UtilityReading> {
    return this.request<UtilityReading>('/utility-readings', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  static async updateUtilityReading(
    id: number,
    payload: {
      previous_index?: number;
      current_index?: number;
      unit_price?: number;
    }
  ): Promise<UtilityReading> {
    return this.request<UtilityReading>(`/utility-readings/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  // ==========================================
  // GLOBAL SEARCH / OMNIBOX (US-23)
  // ==========================================

  static async globalSearch(q: string, limit: number = 10): Promise<SearchResult> {
    const query = new URLSearchParams();
    query.append('q', q);
    query.append('limit', String(limit));
    return this.request<SearchResult>(`/search?${query.toString()}`);
  }

  // ==========================================
  // AUDIT LOGS (US-32)
  // ==========================================

  static async getAuditLogs(params?: {
    page?: number;
    page_size?: number;
    action?: string;
    entity_type?: string;
    from?: string;
    to?: string;
    user_id?: number;
  }): Promise<Page<AuditLog>> {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    if (params?.action) query.append('action', params.action);
    if (params?.entity_type) query.append('entity_type', params.entity_type);
    if (params?.from) query.append('from', params.from);
    if (params?.to) query.append('to', params.to);
    if (params?.user_id) query.append('user_id', String(params.user_id));

    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<Page<AuditLog>>(`/audit-logs${qs}`);
  }

  // ==========================================
  // SYSTEM BACKUPS (US-45)
  // ==========================================

  static async getBackupJobs(params?: {
    page?: number;
    page_size?: number;
    status?: string;
  }): Promise<Page<BackupJob>> {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    if (params?.status) query.append('status', params.status);

    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<Page<BackupJob>>(`/system/backups${qs}`);
  }

  static async triggerBackup(): Promise<BackupJob> {
    return this.request<BackupJob>('/system/backups', {
      method: 'POST',
    });
  }
}
