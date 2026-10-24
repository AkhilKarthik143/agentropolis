import type { EconomyEvent, EconomySummary } from '@/types/economy';

const SIMULATION_ID = 'demo_001';
const API_ROOT = `/api/simulations/${SIMULATION_ID}`;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Economy request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const getEconomySummary = () => request<EconomySummary>('');
export const getEconomyEvents = (since = 0) => request<EconomyEvent[]>(`/events?since=${since}`);
export const getScenarios = async () => {
  const response = await fetch('/api/economy/scenarios');
  if (!response.ok) throw new Error(`Scenario request failed (${response.status})`);
  return response.json() as Promise<{ supported: string[]; clock: string }>;
};
export const triggerShock = (shockType: string, supplierId?: string) => request<Record<string, unknown>>('/shock', { method: 'POST', body: JSON.stringify({ type: shockType, supplier_id: supplierId }) });
export const decideApproval = (approvalId: string, approved: boolean, approver = 'human_operator') => request<Record<string, unknown>>(`/approvals/${approvalId}`, { method: 'POST', body: JSON.stringify({ approved, approver }) });
export const replayEconomy = () => request<Record<string, unknown>>('/replay', { method: 'POST' });


export type BusinessInput = {
  name: string; kind: string; role: string; objective: string; cash_cents: number;
  reserve_cents: number; spend_limit_cents: number; agent_roles: string[];
  inventory_item?: string; low_stock_threshold?: number;
};
export const createBusiness = (input: BusinessInput) => request<{ business: import('@/types/economy').EconomyBusiness }>('/businesses', { method: 'POST', body: JSON.stringify(input) });
export const updateBusiness = (id: string, input: Partial<BusinessInput> & { active?: boolean }) => request<Record<string, unknown>>(`/businesses/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(input) });
export const controlSimulation = (action: 'tick' | 'pause' | 'resume' | 'reset' | 'speed', speed?: number) => request<Record<string, unknown>>(`/${action}`, { method: 'POST', body: speed === undefined ? undefined : JSON.stringify({ speed }) });
export const progressContract = (id: string, action: 'ship' | 'deliver' | 'pay') => request<Record<string, unknown>>(`/contracts/${encodeURIComponent(id)}/${action}`, { method: 'POST' });
export const reconcilePayment = (id: string) => request<Record<string, unknown>>(`/payments/${encodeURIComponent(id)}/reconcile`, { method: 'POST' });
