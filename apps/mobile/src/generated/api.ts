export interface paths {
    "/v1/routing/plan": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Plan */
        post: operations["plan_v1_routing_plan_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** Itinerary */
        Itinerary: {
            /**
             * Start
             * Format: date-time
             */
            start: string;
            /**
             * End
             * Format: date-time
             */
            end: string;
            /** Duration Seconds */
            duration_seconds: number;
            /** Initial Wait Seconds */
            initial_wait_seconds: number;
            /** Elapsed From Requested Departure Seconds */
            elapsed_from_requested_departure_seconds: number | null;
            /** Walking M */
            walking_m: number;
            /** Transfers */
            transfers: number;
            /** Fare Inr */
            fare_inr: number | null;
            /**
             * Fare Status
             * @enum {string}
             */
            fare_status: "known_synthetic_per_boarding" | "unknown" | "free_walking";
            /** Legs */
            legs: components["schemas"]["Leg"][];
            /** Explanations */
            explanations: string[];
        };
        /** Leg */
        Leg: {
            /**
             * Mode
             * @enum {string}
             */
            mode: "WALK" | "BUS" | "SUBWAY";
            /**
             * Start
             * Format: date-time
             */
            start: string;
            /**
             * End
             * Format: date-time
             */
            end: string;
            /** Distance M */
            distance_m: number;
            /** From Lat */
            from_lat: number;
            /** From Lon */
            from_lon: number;
            /** To Lat */
            to_lat: number;
            /** To Lon */
            to_lon: number;
            /** Route Id */
            route_id?: string | null;
            /** Trip Id */
            trip_id?: string | null;
            /** Direction Id */
            direction_id?: string | null;
            /** Wheelchair Status */
            wheelchair_status?: string | null;
        };
        /** PlanRequest */
        PlanRequest: {
            origin: components["schemas"]["Point"];
            destination: components["schemas"]["Point"];
            /**
             * When
             * Format: date-time
             */
            when: string;
            /**
             * Arrive By
             * @default false
             */
            arrive_by: boolean;
            /**
             * Preference
             * @default fastest
             * @enum {string}
             */
            preference: "fastest" | "cheapest" | "fewest_transfers" | "least_walking";
            /**
             * Modes
             * @default [
             *       "BUS",
             *       "SUBWAY",
             *       "WALK"
             *     ]
             */
            modes: ("BUS" | "SUBWAY" | "WALK")[];
            /**
             * Max Walk M
             * @default 2000
             */
            max_walk_m: number;
            /**
             * Max Transfers
             * @default 3
             */
            max_transfers: number;
            /**
             * Wheelchair
             * @default false
             */
            wheelchair: boolean;
            /**
             * Transit Required
             * @default false
             */
            transit_required: boolean;
            /**
             * Limit
             * @default 5
             */
            limit: number;
            /** Graph Id */
            graph_id?: string | null;
        };
        /** PlanResponse */
        PlanResponse: {
            /**
             * Contract Version
             * @default 1
             * @constant
             */
            contract_version: "1";
            /** Graph Id */
            graph_id: string;
            /** Graph Sha256 */
            graph_sha256: string;
            /** Source Attribution */
            source_attribution: string;
            /** Source License */
            source_license: string;
            /** Otp Version */
            otp_version: string;
            /**
             * Data Mode
             * @default simulation
             * @constant
             */
            data_mode: "simulation";
            /**
             * Confidence
             * @default authored_fixture_only
             * @constant
             */
            confidence: "authored_fixture_only";
            /**
             * Realtime Status
             * @default unavailable
             * @constant
             */
            realtime_status: "unavailable";
            /**
             * Service Status
             * @default unknown
             * @constant
             */
            service_status: "unknown";
            /**
             * Disruption Overlay Applied
             * @default false
             * @constant
             */
            disruption_overlay_applied: false;
            /**
             * Congestion Safety Verified
             * @default false
             * @constant
             */
            congestion_safety_verified: false;
            /**
             * Status
             * @enum {string}
             */
            status: "ok" | "no_route";
            /** Reason */
            reason?: string | null;
            /** Preference */
            preference: string;
            /**
             * Ranking Scope
             * @default bounded_provider_candidates
             * @constant
             */
            ranking_scope: "bounded_provider_candidates";
            /** Itineraries */
            itineraries: components["schemas"]["Itinerary"][];
        };
        /** Point */
        Point: {
            /** Stop Id */
            stop_id?: string | null;
            /** Latitude */
            latitude?: number | null;
            /** Longitude */
            longitude?: number | null;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    plan_v1_routing_plan_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PlanRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PlanResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
