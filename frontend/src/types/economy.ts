export type EconomyEvent = {
  seq: number;
  ts: string;
  type: string;
  session_id?: string | null;
  business_id?: string | null;
  deal_id?: string | null;
  correlation_id?: string | null;
  causation_id?: string | null;
  payload: Record<string, unknown>;
};

export type EconomyBusiness = {
  business_id: string;
  name: string;
  kind: string;
  role: string;
  reliability: number;
  reserve_cents: number;
  spend_limit_cents: number;
  categories: string[];
  inventory: Record<string, number>;
  cash_cents: number;
  account_id: string;
  active: boolean;
  bank: string;
  objective?: string;
  credit_status?: string;
  credit_score?: number;
  credit_reason?: string;
  supplier_note?: string;
};

export type EconomyContract = {
  contract_id: string;
  buyer_id: string;
  supplier_id: string;
  item: string;
  quantity: number;
  unit_price_cents: number;
  total_cents: number;
  delivery_days: number;
  status: string;
  proposal_id: string;
  rationale: string;
  reliability: number;
  state?: string;
};

export type EconomyOffer = {
  supplier_id: string;
  score: number;
  offer: {
    proposal_id: string;
    item?: string;
    quantity?: number;
    unit_price_cents?: number;
    delivery_days?: number;
    public_rationale?: string;
  };
  score_breakdown: {
    factors: Record<string, { raw: number; weight: number; contribution: number }>;
    inputs: Record<string, number>;
  };
  reliability_report?: { mode?: string; status?: string; tx_hash?: string };
};

export type EconomyApproval = {
  approval_id: string;
  proposal_id: string;
  business_id: string;
  amount_cents: number;
  proposer: string;
  status: 'pending' | 'granted' | 'denied';
  approver?: string | null;
  reason: string;
};

export type LedgerLine = { account: string; amount_cents: number; business_id: string; memo: string };
export type LedgerEntry = { entry_id: string; business_id: string; memo: string; idempotency_key?: string | null; lines: LedgerLine[] };
export type FinancePurchaseOrder = { po_id: string; supplier_id: string; item: string; quantity: number; total_cents: number; payment_terms: string; cost_center: string };
export type FinanceInvoice = { invoice_id: string; invoice_number: string; po_id: string; amount_cents: number; due_date: string; payment_terms: string; tax_cents: number; cost_center: string };
export type FinanceMatch = { match_id: string; po_id: string; invoice_id: string; receipt_id: string; status: string; reasons: string[] };
export type FinanceSnapshot = { purchase_orders: FinancePurchaseOrder[]; receipts: Record<string, unknown>[]; invoices: FinanceInvoice[]; matches: FinanceMatch[] };

export type EconomySummary = {
  simulation_id?: string;
  status?: string;
  mode: string;
  clock: string;
  businesses: EconomyBusiness[];
  offers?: EconomyOffer[];
  contracts: EconomyContract[];
  approvals: EconomyApproval[];
  ledger: LedgerEntry[];
  trial_balance: Record<string, number>;
  ledger_proof?: { balanced: boolean; total_debits_cents: number; total_credits_cents: number };
  finance?: FinanceSnapshot;
  audit?: { valid: boolean; event_count?: number; first_break_seq?: number | null; reason?: string };
  events: EconomyEvent[];
};

