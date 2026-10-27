import { z } from 'zod';
import type { PlanResponse } from './types';

const timestamp = z.string().datetime({ offset: true });
const leg = z
  .object({
    mode: z.enum(['WALK', 'BUS', 'SUBWAY']),
    start: timestamp,
    end: timestamp,
    distance_m: z.number().finite().nonnegative(),
    from_lat: z.number().min(-90).max(90),
    from_lon: z.number().min(-180).max(180),
    to_lat: z.number().min(-90).max(90),
    to_lon: z.number().min(-180).max(180),
    route_id: z.string().nullable().optional(),
    trip_id: z.string().nullable().optional(),
    direction_id: z.string().nullable().optional(),
    wheelchair_status: z.string().nullable().optional(),
  })
  .refine((v) => Date.parse(v.end) >= Date.parse(v.start));
export const responseSchema = z
  .object({
    contract_version: z.literal('1'),
    graph_id: z.string().regex(/^[a-f0-9]{64}$/),
    graph_sha256: z.string().regex(/^[a-f0-9]{64}$/),
    source_attribution: z.string(),
    source_license: z.string(),
    otp_version: z.string(),
    data_mode: z.literal('simulation'),
    confidence: z.literal('authored_fixture_only'),
    realtime_status: z.literal('unavailable'),
    service_status: z.literal('unknown'),
    disruption_overlay_applied: z.literal(false),
    congestion_safety_verified: z.literal(false),
    status: z.enum(['ok', 'no_route']),
    reason: z.string().nullable(),
    preference: z.string(),
    ranking_scope: z.literal('bounded_provider_candidates'),
    itineraries: z
      .array(
        z.object({
          start: timestamp,
          end: timestamp,
          duration_seconds: z.number().int().nonnegative(),
          initial_wait_seconds: z.number().int().nonnegative(),
          elapsed_from_requested_departure_seconds: z
            .number()
            .int()
            .nonnegative()
            .nullable(),
          walking_m: z.number().finite().nonnegative(),
          transfers: z.number().int().nonnegative(),
          fare_inr: z.number().int().nonnegative().nullable(),
          fare_status: z.enum([
            'known_synthetic_per_boarding',
            'unknown',
            'free_walking',
          ]),
          legs: z.array(leg).min(1).max(64),
          explanations: z.array(z.string()),
        }),
      )
      .max(10),
  })
  .refine((v) =>
    v.status === 'ok' ? v.itineraries.length > 0 : v.itineraries.length === 0,
  );
export function parsePlan(value: unknown): PlanResponse {
  return responseSchema.parse(value);
}
