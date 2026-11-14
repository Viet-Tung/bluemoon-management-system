export type RoleCode = 'ADMIN' | 'ACCOUNTANT' | 'TREASURER' | 'RESIDENT';

export interface User {
  id: number;
  username: string;
  full_name: string;
  email?: string;
  phone?: string;
  role: {
    id: number;
    code: RoleCode;
    name: string;
    description?: string;
  };
  household_id?: number | null;
  is_active: boolean;
  must_change_password?: boolean;
  last_login_at?: string | null;
  created_at: string;
}

export interface Apartment {
  id: number;
  code: string;
  floor: number;
  area_m2: number;
  status: 'ACTIVE' | 'INACTIVE';
  note?: string;
  current_household?: {
    id: number;
    household_code: string;
    head_name?: string;
    contact_phone?: string;
    member_count: number;
  } | null;
}

export interface Household {
  id: number;
  household_code: string;
  status: 'ACTIVE' | 'INACTIVE';
  contact_phone?: string;
  contact_email?: string;
  note?: string;
  apartment?: {
    id: number;
    code: string;
    floor: number;
    area_m2: number;
  } | null;
  head_resident?: Resident | null;
  member_count: number;
  credit_balance?: number;
  total_debt?: number;
  occupancy_start_date?: string;
}

export interface Resident {
  id: number;
  household_id: number;
  full_name: string;
  date_of_birth: string;
  gender: 'NAM' | 'NU' | 'KHAC';
  cccd?: string;
  phone?: string;
  email?: string;
  relationship_to_head?: string;
  is_head: boolean;
  residence_status: 'THUONG_TRU' | 'TAM_VANG' | 'DA_CHUYEN_DI' | 'DA_QUA_DOI';
  status_effective_date?: string;
  status_reason?: string;
  is_deleted?: boolean;
}

export interface TemporaryStay {
  id: number;
  type: 'TAM_TRU' | 'TAM_VANG';
  household_id: number;
  apartment_code?: string;
  full_name: string;
  cccd?: string;
  permanent_address?: string;
  destination?: string;
  start_date: string;
  end_date: string;
  days_left: number;
  status: 'ACTIVE' | 'EXPIRED' | 'ENDED';
  reason?: string;
}

export interface FeeType {
  id: number;
  code: string;
  name: string;
  fee_group: 'MANAGEMENT' | 'PARKING' | 'UTILITY' | 'OTHER';
  calc_method: 'PER_M2' | 'PER_HOUSEHOLD' | 'PER_PERSON' | 'PER_VEHICLE' | 'METERED';
  unit_label: string;
  vehicle_type?: 'MOTORBIKE' | 'CAR' | 'BICYCLE' | null;
  is_pass_through: boolean;
  cycle: 'MONTHLY' | 'QUARTERLY' | 'YEARLY';
  due_day?: number;
  status: 'ACTIVE' | 'INACTIVE';
  description?: string;
  current_unit_price?: number;
}

export interface FeeRate {
  id: number;
  fee_type_id: number;
  unit_price: number;
  effective_from: string;
  effective_to?: string | null;
}

export interface FeeExemption {
  id: number;
  household_id: number;
  household_code: string;
  fee_type_id: number;
  fee_name: string;
  discount_type: 'PERCENT' | 'AMOUNT';
  discount_value: number;
  reason: string;
  decision_no?: string;
  approved_by_name?: string;
  valid_from: string;
  valid_to?: string | null;
  status: 'ACTIVE' | 'REVOKED';
}

export interface BillingPeriod {
  id: number;
  period_month: string; // YYYY-MM-01
  name: string;
  due_date: string;
  status: 'DRAFT' | 'OPEN' | 'CLOSED';
  generated_at?: string | null;
  closed_at?: string | null;
  total_invoices?: number;
  total_receivable?: number;
  total_collected?: number;
}

export interface InvoiceItem {
  id: number;
  fee_type_id: number;
  fee_code: string;
  fee_name: string;
  fee_group: string;
  quantity: number;
  unit_price: number;
  gross_amount: number;
  discount_amount: number;
  net_amount: number;
  paid_amount: number;
  description?: string;
}

export interface Invoice {
  id: number;
  billing_period_id: number;
  period_name: string;
  household_id: number;
  household_code: string;
  apartment_code: string;
  head_name: string;
  contact_phone?: string;
  apartment_area: number;
  fee_amount: number;
  discount_amount: number;
  previous_debt: number;
  credit_applied: number;
  total_due: number;
  paid_amount: number;
  remaining_amount: number;
  status: 'UNPAID' | 'PARTIAL' | 'PAID';
  created_at: string;
  items: InvoiceItem[];
}

export interface PaymentAllocation {
  id: number;
  invoice_item_id: number;
  fee_name: string;
  amount: number;
}

export interface Payment {
  id: number;
  receipt_no: string;
  household_id: number;
  household_code: string;
  apartment_code: string;
  payer_name: string;
  paid_at: string;
  amount: number;
  allocated_amount: number;
  credit_amount: number;
  method: 'CASH' | 'BANK_TRANSFER';
  reference_no?: string;
  collected_by_name: string;
  status: 'VALID' | 'CANCELLED';
  cancel_reason?: string;
  cancelled_by_name?: string;
  cancelled_at?: string;
  print_count: number;
  allocations: PaymentAllocation[];
}

export interface DonationCampaign {
  id: number;
  code: string;
  name: string;
  description?: string;
  start_date: string;
  end_date?: string | null;
  status: 'DRAFT' | 'ACTIVE' | 'CLOSED';
  total_raised: number;
  total_donors: number;
}

export interface Donation {
  id: number;
  campaign_id: number;
  campaign_name: string;
  household_id: number;
  household_code: string;
  apartment_code: string;
  donor_name: string;
  voucher_no: string;
  amount: number;
  donated_at: string;
  method: 'CASH' | 'BANK_TRANSFER';
  status: 'VALID' | 'CANCELLED';
  cancel_reason?: string;
  collected_by_name: string;
}

export interface ProfileChangeRequest {
  id: number;
  household_id: number;
  household_code: string;
  apartment_code: string;
  requested_by_username: string;
  request_type: 'UPDATE_RESIDENT' | 'ADD_RESIDENT' | 'UPDATE_HOUSEHOLD';
  proposed_data: Record<string, any>;
  evidence_files: string[];
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  reject_reason?: string;
  reviewed_by_name?: string;
  reviewed_at?: string;
  created_at: string;
}

export interface AuditLog {
  id: number;
  user_id?: number | null;
  username?: string | null;
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
  requested_by_name?: string | null;
  requested_at: string;
  finished_at?: string | null;
  size_bytes?: number | null;
  file_path?: string | null;
  error_message?: string | null;
}
