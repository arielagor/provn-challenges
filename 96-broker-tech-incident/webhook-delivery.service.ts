// webhook-delivery.service.ts
//
// Revised webhook delivery for the shipment-events consumer.
//
// What this fixes from the original:
//   1. SQL injection via string interpolation (extra issue beyond the primary incident)
//   2. No idempotency on webhook delivery, so consumer retries produced duplicate side effects
//   3. Recursive retry that re-fetched the broker list and rebroadcast to brokers that already succeeded
//   4. No backoff, no retry cap, no DLQ
//   5. Unstructured single-string logging
//   6. JSON.parse with no validation
//
// Constraints honored:
//   - TypeScript + Node.js, no new runtime
//   - Idempotency keys persisted to Redis (configurable to a DB if Redis unavailable)
//   - Kafka topic and partition schema unchanged. Idempotency key derives from
//     (topic, partition, offset, broker_id) which is stable without touching Kafka config.
//   - Written for the 2am on-call engineer. Every log line names the event_id and
//     broker_id so a single grep on either narrows scope to the failure.

import { z } from 'zod';

// --- Types ---

export interface KafkaMessage {
  topic: string;
  partition: number;
  offset: string; // string-form long, never number (52-bit precision risk)
  value: Buffer;
}

export interface HttpClient {
  post(
    url: string,
    body: unknown,
    opts: { timeout: number; headers?: Record<string, string> },
  ): Promise<{ status: number }>;
}

export interface IdempotencyStore {
  // SET-IF-NOT-EXISTS with TTL. Returns true if this caller acquired the key.
  // Returns false if the key was already held (means another delivery succeeded
  // or is in flight). Implemented by SET NX EX in Redis.
  acquire(key: string, ttlSeconds: number): Promise<boolean>;
  // Release on a non-permanent failure so a future redelivery can claim it.
  release(key: string): Promise<void>;
}

export interface DatabaseService {
  // Parameterized query. The implementation is responsible for binding $1..$n.
  query<T = unknown>(sql: string, params: unknown[]): Promise<T[]>;
}

export interface DeadLetter {
  record(
    eventId: string,
    brokerId: string,
    payload: unknown,
    reason: string,
    httpStatus?: number,
  ): Promise<void>;
}

export interface StructuredLogger {
  info(msg: string, ctx: Record<string, unknown>): void;
  warn(msg: string, ctx: Record<string, unknown>): void;
  error(msg: string, ctx: Record<string, unknown>): void;
}

export interface Sleep {
  (ms: number): Promise<void>;
}

const ShipmentEventSchema = z.object({
  loadId: z.string().min(1),
  status: z.enum(['matched', 'accepted', 'in-transit', 'delivered', 'cancelled']),
  occurredAt: z.string().min(1), // ISO-8601 from upstream
  // Pass through any other fields untouched. We do not strip.
}).passthrough();
export type ShipmentEvent = z.infer<typeof ShipmentEventSchema>;

interface BrokerSubscription {
  id: string;
  webhookUrl: string;
  // Optional shared secret used by callers downstream to verify HMAC.
  // Out of scope for this PR; see scope note in README Section A.
}

// --- Service ---

export class WebhookDeliveryService {
  private readonly maxAttempts = 5;
  private readonly baseBackoffMs = 250;
  private readonly idempotencyTtlSeconds = 60 * 60 * 24 * 7; // one week, tunable
  private readonly httpTimeoutMs = 5000;

  constructor(
    private readonly http: HttpClient,
    private readonly db: DatabaseService,
    private readonly idempotency: IdempotencyStore,
    private readonly dlq: DeadLetter,
    private readonly log: StructuredLogger,
    private readonly sleep: Sleep,
  ) {}

  async processShipmentEvent(event: KafkaMessage): Promise<void> {
    const eventId = `${event.topic}:${event.partition}:${event.offset}`;
    let payload: ShipmentEvent;

    try {
      const raw = JSON.parse(event.value.toString());
      payload = ShipmentEventSchema.parse(raw);
    } catch (err) {
      // Permanent: malformed events should not loop forever. Park and move on.
      this.log.error('payload_invalid', {
        eventId,
        error: err instanceof Error ? err.message : String(err),
      });
      await this.dlq.record(eventId, 'unknown', null, 'payload_invalid');
      return;
    }

    let brokers: BrokerSubscription[];
    try {
      brokers = await this.db.query<BrokerSubscription>(
        'SELECT id, "webhookUrl" FROM broker_subscriptions WHERE load_id = $1',
        [payload.loadId],
      );
    } catch (err) {
      // Treat DB failure as transient. Throwing back to the consumer triggers
      // Kafka redelivery, which is the right behavior.
      this.log.error('subscription_lookup_failed', {
        eventId,
        loadId: payload.loadId,
        error: err instanceof Error ? err.message : String(err),
      });
      throw err;
    }

    // Per-broker delivery is independent. One broker's failure must not block
    // delivery to the others. Errors are caught per broker and tallied.
    let permanentFailures = 0;
    for (const broker of brokers) {
      try {
        await this.deliverToBroker(eventId, broker, payload);
      } catch (err) {
        // deliverToBroker only throws on transient failure that exhausted
        // retries, which is recorded to DLQ inside the method. We log here
        // for visibility but do not rethrow, so other brokers are not blocked.
        permanentFailures += 1;
        this.log.error('broker_delivery_exhausted', {
          eventId,
          brokerId: broker.id,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }

    this.log.info('event_processed', {
      eventId,
      loadId: payload.loadId,
      status: payload.status,
      brokerCount: brokers.length,
      permanentFailures,
    });
  }

  private async deliverToBroker(
    eventId: string,
    broker: BrokerSubscription,
    payload: ShipmentEvent,
  ): Promise<void> {
    const idempotencyKey = `webhook:${eventId}:${broker.id}`;
    const acquired = await this.idempotency.acquire(idempotencyKey, this.idempotencyTtlSeconds);
    if (!acquired) {
      // Already delivered (or in flight from a parallel pod). This is the
      // exact case that produced the 847 duplicates in INC-4471. Do nothing.
      this.log.info('webhook_skipped_duplicate', {
        eventId,
        brokerId: broker.id,
      });
      return;
    }

    let attempt = 0;
    while (attempt < this.maxAttempts) {
      attempt += 1;
      const t0 = Date.now();
      try {
        const res = await this.http.post(broker.webhookUrl, payload, {
          timeout: this.httpTimeoutMs,
          headers: {
            'X-Idempotency-Key': idempotencyKey,
            'X-Event-Id': eventId,
            'Content-Type': 'application/json',
          },
        });
        if (res.status >= 200 && res.status < 300) {
          this.log.info('webhook_delivered', {
            eventId,
            brokerId: broker.id,
            attempt,
            status: res.status,
            latencyMs: Date.now() - t0,
          });
          return;
        }
        if (this.isRetryable(res.status)) {
          this.log.warn('webhook_retryable_failure', {
            eventId,
            brokerId: broker.id,
            attempt,
            status: res.status,
            latencyMs: Date.now() - t0,
          });
        } else {
          // 4xx (other than 408/429) means the broker's TMS rejected the
          // payload as malformed or unauthorized. Retrying will not help.
          this.log.error('webhook_permanent_failure', {
            eventId,
            brokerId: broker.id,
            attempt,
            status: res.status,
            latencyMs: Date.now() - t0,
          });
          await this.dlq.record(eventId, broker.id, payload, 'http_rejected', res.status);
          return;
        }
      } catch (err) {
        // Network errors and timeouts are transient.
        this.log.warn('webhook_network_error', {
          eventId,
          brokerId: broker.id,
          attempt,
          error: err instanceof Error ? err.message : String(err),
          latencyMs: Date.now() - t0,
        });
      }

      if (attempt < this.maxAttempts) {
        await this.sleep(this.backoffMs(attempt));
      }
    }

    // All attempts exhausted on transient failures. Release the idempotency
    // key so a future intentional retry (e.g. operator-driven) can re-attempt.
    await this.idempotency.release(idempotencyKey);
    await this.dlq.record(eventId, broker.id, payload, 'retries_exhausted');
    throw new Error(`delivery exhausted: eventId=${eventId} brokerId=${broker.id}`);
  }

  private isRetryable(status: number): boolean {
    if (status >= 500) return true;
    if (status === 408) return true; // request timeout
    if (status === 429) return true; // rate limited
    return false;
  }

  private backoffMs(attempt: number): number {
    // Exponential with full jitter (AWS pattern). attempt is 1-indexed.
    // Caps growth at 8s so a slow broker does not stall the consumer.
    const ceiling = Math.min(this.baseBackoffMs * 2 ** (attempt - 1), 8000);
    return Math.floor(Math.random() * ceiling);
  }
}
