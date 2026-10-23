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

