import type { PlanRequest, PlanResponse } from './types';
import { parsePlan } from './validation';

export class ClientError extends Error {
  constructor(
    public code: 'unauthorized' | 'offline' | 'invalid' | 'incompatible',
  ) {
    super(code);
  }
}
export interface TokenSource {
  token(): Promise<string | null>;
  refresh(): Promise<string | null>;
}
export function apiClient(
  base: string,
  auth: TokenSource,
  fetcher: typeof fetch = fetch,
) {
  return {
    async plan(request: PlanRequest): Promise<PlanResponse> {
      let token = await auth.token();
      if (!token) throw new ClientError('unauthorized');
      for (let attempt = 0; attempt < 2; attempt++) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 12000);
        let response: Response;
        try {
          response = await fetcher(`${base}/v1/routing/plan`, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(request),
            signal: controller.signal,
            redirect: 'error',
          });
          if (response.status === 401 && attempt === 0) {
            token = await auth.refresh();
            if (!token) throw new ClientError('unauthorized');
            continue;
          }
          if (response.status === 401 || response.status === 403)
            throw new ClientError('unauthorized');
          if (response.status === 409 || response.status === 422)
            throw new ClientError('invalid');
          if (!response.ok) throw new ClientError('offline');
          const body = await response.text();
          if (body.length > 2000000) throw new ClientError('incompatible');
          try {
            return parsePlan(JSON.parse(body));
          } catch {
            throw new ClientError('incompatible');
          }
        } catch (error) {
          if (error instanceof ClientError) throw error;
          throw new ClientError('offline');
        } finally {
          clearTimeout(timer);
        }
      }
      throw new ClientError('unauthorized');
    },
    async health(): Promise<boolean> {
      try {
        const response = await fetcher(`${base}/health/ready`, {
          signal: AbortSignal.timeout(5000),
          redirect: 'error',
        });
        return response.ok;
      } catch {
        return false;
      }
    },
  };
}
