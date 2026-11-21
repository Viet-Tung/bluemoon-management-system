export type RoleCode = 'ADMIN' | 'ACCOUNTANT' | 'TREASURER' | 'RESIDENT';

export interface Role {
  id: number;
  code: RoleCode;
  name: string;
  description?: string | null;
}

export interface User {
  id: number;
  username: string;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  role: Role;
  household_id?: number | null;
  is_active: boolean;
  must_change_password?: boolean;
  locked_until?: string | null;
  last_login_at?: string | null;
}

export interface UserWithTempPassword extends User {
  temporary_password: string;
}

export interface Apartment {
  id: number;
  code: string;
  floor: number;
  area_m2: number;
  status: 'ACTIVE' | 'INACTIVE';
  note?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Household {
  id: number;
  household_code: string;
  status: 'ACTIVE' | 'INACTIVE';
  contact_phone?: string | null;
  contact_email?: string | null;
  note?: string | null;
  apartment_id?: number | null;
  apartment_code?: string | null;
  floor?: number | null;
  area_m2?: number | null;
  head_resident_id?: number | null;
  head_name?: string | null;
  head_phone?: string | null;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface ResidentAccount {
  username: string;
  temporary_password: string;
}

export interface HouseholdCreated extends Household {
  resident_account?: ResidentAccount | null;
}

export type FeeGroup = 'MANAGEMENT' | 'PARKING' | 'UTILITY' | 'OTHER';
export type CalcMethod = 'PER_M2' | 'PER_HOUSEHOLD' | 'PER_PERSON' | 'PER_VEHICLE' | 'METERED';
export type VehicleType = 'MOTORBIKE' | 'CAR' | 'BICYCLE';
export type FeeCycle = 'MONTHLY' | 'QUARTERLY' | 'YEARLY';
export type FeeStatus = 'ACTIVE' | 'INACTIVE';

export interface FeeType {
  id: number;
  code: string;
  name: string;
  fee_group: FeeGroup;
  calc_method: CalcMethod;
  unit_label: string;
  vehicle_type?: VehicleType | null;
  is_pass_through: boolean;
  provider_id?: number | null;
  cycle: FeeCycle;
  due_day?: number | null;
  status: FeeStatus;
  description?: string | null;
  current_unit_price?: number | null;
  created_at: string;
  updated_at: string;
}

export interface AuditLog {
  id: number;
  user_id?: number | null;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  old_value?: Record<string, any> | null;
  new_value?: Record<string, any> | null;
  reason?: string | null;
  ip_address?: string | null;
  user_agent?: string | null;
  created_at: string;
}

export interface BackupJob {
  id: number;
  status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED';
  requested_by?: number | null;
  requested_at: string;
  finished_at?: string | null;
  size_bytes?: number | null;
}

export interface Page<T> {
  page: number;
  page_size: number;
  total: number;
  total_pages?: number;
  items: T[];
}

export interface ApiErrorDetail {
  field?: string;
  message: string;
}
