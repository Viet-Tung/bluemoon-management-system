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
  row?: number;
}

// ==========================================
// SPRINT 2 DOMAIN TYPES
// ==========================================

export type Gender = 'NAM' | 'NU' | 'KHAC';
export type ResidenceStatus = 'THUONG_TRU' | 'TAM_VANG' | 'DA_CHUYEN_DI' | 'DA_QUA_DOI';

export interface Resident {
  id: number;
  household_id: number;
  full_name: string;
  date_of_birth: string;
  gender: Gender | string;
  cccd?: string | null;
  phone?: string | null;
  email?: string | null;
  relationship_to_head?: string | null;
  is_head: boolean;
  residence_status: ResidenceStatus | string;
  status_effective_date?: string | null;
  status_reason?: string | null;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface ImportResult {
  total_rows: number;
  imported_rows: number;
}

export interface FeeRate {
  id: number;
  fee_type_id: number;
  unit_price: number;
  effective_from: string;
  effective_to?: string | null;
  created_by?: number | null;
  created_at: string;
}

export type DiscountType = 'PERCENT' | 'AMOUNT';
export type ExemptionStatus = 'ACTIVE' | 'REVOKED';

export interface FeeExemption {
  id: number;
  household_id: number;
  fee_type_id: number;
  discount_type: DiscountType;
  discount_value: number;
  reason: string;
  decision_no?: string | null;
  approved_by?: number | null;
  valid_from: string;
  valid_to?: string | null;
  status: ExemptionStatus;
  created_at: string;
  updated_at: string;
}

export type VehicleStatus = 'ACTIVE' | 'INACTIVE';

export interface Vehicle {
  id: number;
  household_id: number;
  plate_number: string;
  vehicle_type: VehicleType;
  brand?: string | null;
  color?: string | null;
  status: VehicleStatus;
  registered_date: string;
  unregistered_date?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export type BillingPeriodStatus = 'DRAFT' | 'OPEN' | 'CLOSED';
export type InvoiceStatus = 'UNPAID' | 'PARTIAL' | 'PAID';

export interface BillingPeriod {
  id: number;
  period_month: string;
  name: string;
  due_date?: string | null;
  status: BillingPeriodStatus;
  generated_at?: string | null;
  closed_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface GenerateResult {
  households_processed: number;
  invoices_created: number;
  total_fee_amount: number;
}

export interface InvoiceItem {
  id: number;
  invoice_id: number;
  fee_type_id: number;
  fee_name: string;
  quantity: number;
  unit_price: number;
  gross_amount: number;
  discount_amount: number;
  net_amount: number;
  paid_amount: number;
  description?: string | null;
}

export interface Invoice {
  id: number;
  billing_period_id?: number | null;
  household_id: number;
  household_code: string;
  apartment_id?: number | null;
  apartment_code?: string | null;
  apartment_area: number;
  fee_amount: number;
  discount_amount: number;
  previous_debt: number;
  credit_applied: number;
  total_due: number;
  paid_amount: number;
  status: InvoiceStatus;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface InvoiceDetail extends Invoice {
  items: InvoiceItem[];
}

export interface UtilityReading {
  id: number;
  household_id: number;
  household_code: string;
  fee_type_id: number;
  fee_name: string;
  billing_period_id: number;
  previous_index: number;
  current_index: number;
  consumption: number;
  unit_price: number;
  amount: number;
  recorded_by?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export type SearchEntityType = 'HOUSEHOLD' | 'APARTMENT' | 'RESIDENT' | 'VEHICLE';

export interface SearchHit {
  entity_type: SearchEntityType;
  entity_id: number;
  household_id?: number | null;
  title: string;
  subtitle?: string | null;
}

export interface SearchResult {
  items: SearchHit[];
}
