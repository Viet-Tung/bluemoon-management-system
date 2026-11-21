import {
  Apartment,
  AuditLog,
  BackupJob,
  FeeType,
  Household,
  HouseholdCreated,
  Page,
  Role,
  User,
  UserWithTempPassword,
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
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);

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
          'Yêu cầu kết nối quá thời gian chờ (8s). Máy chủ Backend không phản hồi.',
          408
        );
      }

      // Failed to fetch: backend service is offline
      throw new ApiError(
        'BACKEND_OFFLINE',
        'Không thể kết nối đến máy chủ Backend (http://localhost:8000). Vui lòng kiểm tra dịch vụ Backend.',
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
    apartment_id?: number;
    status?: string;
  }): Promise<Page<Household>> {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    if (params?.apartment_id) query.append('apartment_id', String(params.apartment_id));
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

  // ==========================================
  // AUDIT LOGS (US-32)
  // ==========================================

  static async getAuditLogs(params?: {
    page?: number;
    page_size?: number;
    action?: string;
    entity_type?: string;
    from_date?: string;
    to_date?: string;
    user_id?: number;
  }): Promise<Page<AuditLog>> {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    if (params?.action) query.append('action', params.action);
    if (params?.entity_type) query.append('entity_type', params.entity_type);
    if (params?.from_date) query.append('from_date', params.from_date);
    if (params?.to_date) query.append('to_date', params.to_date);
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
