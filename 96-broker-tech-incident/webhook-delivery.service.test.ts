// webhook-delivery.service.test.ts
//
// Focused tests on the behaviors that fix INC-4471. Not exhaustive.
// Run with: npx vitest run (or jest equivalent)

import { describe, it, expect, beforeEach } from 'vitest';
import {
  WebhookDeliveryService,
  HttpClient,
  IdempotencyStore,
  DatabaseService,
  DeadLetter,
  StructuredLogger,
  Sleep,
  KafkaMessage,
} from './webhook-delivery.service';

// --- Test doubles ---

class FakeIdempotency implements IdempotencyStore {
  private held = new Set<string>();
  acquired: string[] = [];
  released: string[] = [];
  async acquire(key: string): Promise<boolean> {
    if (this.held.has(key)) return false;
    this.held.add(key);
    this.acquired.push(key);
    return true;
  }
  async release(key: string): Promise<void> {
    this.held.delete(key);
    this.released.push(key);
  }
}

class FakeHttp implements HttpClient {
  calls: { url: string; body: unknown; headers?: Record<string, string> }[] = [];
  // Per-URL queued responses (FIFO). Anything not queued returns 200.
  responses: Map<string, ({ status: number } | { throw: string })[]> = new Map();
  async post(url: string, body: unknown, opts: { timeout: number; headers?: Record<string, string> }) {
    this.calls.push({ url, body, headers: opts.headers });
    const queue = this.responses.get(url) ?? [];
    const next = queue.shift();
    if (next && 'throw' in next) throw new Error(next.throw);
    return next ?? { status: 200 };
  }
}

class FakeDb implements DatabaseService {
  rows: unknown[] = [];
  lastSql = '';
  lastParams: unknown[] = [];
  async query<T>(sql: string, params: unknown[]): Promise<T[]> {
    this.lastSql = sql;
    this.lastParams = params;
    return this.rows as T[];
  }
}

class FakeDlq implements DeadLetter {
  entries: { eventId: string; brokerId: string; reason: string; status?: number }[] = [];
  async record(eventId: string, brokerId: string, _payload: unknown, reason: string, status?: number) {
    this.entries.push({ eventId, brokerId, reason, status });
  }
}

class FakeLogger implements StructuredLogger {
  events: { level: string; msg: string; ctx: Record<string, unknown> }[] = [];
  info(msg: string, ctx: Record<string, unknown>) { this.events.push({ level: 'info', msg, ctx }); }
  warn(msg: string, ctx: Record<string, unknown>) { this.events.push({ level: 'warn', msg, ctx }); }
  error(msg: string, ctx: Record<string, unknown>) { this.events.push({ level: 'error', msg, ctx }); }
  has(msg: string): boolean { return this.events.some(e => e.msg === msg); }
}

const noSleep: Sleep = async () => {};

const makeMessage = (loadId = 'L-1', offset = '100'): KafkaMessage => ({
  topic: 'shipment-events',
  partition: 0,
  offset,
  value: Buffer.from(JSON.stringify({
    loadId,
    status: 'matched',
    occurredAt: '2026-04-30T12:00:00Z',
  })),
});

const setup = () => {
  const http = new FakeHttp();
  const db = new FakeDb();
  const idem = new FakeIdempotency();
  const dlq = new FakeDlq();
  const log = new FakeLogger();
  const svc = new WebhookDeliveryService(http, db, idem, dlq, log, noSleep);
  return { http, db, idem, dlq, log, svc };
};

// --- Tests ---

describe('idempotency', () => {
  it('delivers once on first call and skips on second call for the same event+broker', async () => {
    const { http, db, idem, log, svc } = setup();
    db.rows = [{ id: 'B1', webhookUrl: 'https://b1.example/hook' }];
    const msg = makeMessage();
    await svc.processShipmentEvent(msg);
    await svc.processShipmentEvent(msg);
    expect(http.calls.length).toBe(1);
    expect(idem.acquired).toEqual(['webhook:shipment-events:0:100:B1']);
    expect(log.has('webhook_skipped_duplicate')).toBe(true);
  });

  it('uses per-broker idempotency keys so one broker failing does not block another', async () => {
    const { http, db, idem, svc } = setup();
    db.rows = [
      { id: 'B1', webhookUrl: 'https://b1/hook' },
      { id: 'B2', webhookUrl: 'https://b2/hook' },
    ];
    await svc.processShipmentEvent(makeMessage());
    expect(idem.acquired).toEqual([
      'webhook:shipment-events:0:100:B1',
      'webhook:shipment-events:0:100:B2',
    ]);
    expect(http.calls.map(c => c.url)).toEqual(['https://b1/hook', 'https://b2/hook']);
  });
});

describe('error classification', () => {
  it('does not retry on 4xx (other than 408/429) and records to DLQ', async () => {
    const { http, db, dlq, svc } = setup();
    db.rows = [{ id: 'B1', webhookUrl: 'https://b1/hook' }];
    http.responses.set('https://b1/hook', [{ status: 401 }]);
    await svc.processShipmentEvent(makeMessage());
    expect(http.calls.length).toBe(1);
    expect(dlq.entries).toEqual([{
      eventId: 'shipment-events:0:100',
      brokerId: 'B1',
      reason: 'http_rejected',
      status: 401,
    }]);
  });

  it('retries 5xx with bounded attempts then DLQs', async () => {
    const { http, db, dlq, idem, svc } = setup();
    db.rows = [{ id: 'B1', webhookUrl: 'https://b1/hook' }];
    http.responses.set('https://b1/hook', [
      { status: 503 }, { status: 503 }, { status: 503 }, { status: 503 }, { status: 503 },
    ]);
    await svc.processShipmentEvent(makeMessage());
    expect(http.calls.length).toBe(5);
    expect(dlq.entries[0].reason).toBe('retries_exhausted');
    // Idempotency key is released so a future intentional retry can claim it.
    expect(idem.released).toEqual(['webhook:shipment-events:0:100:B1']);
  });

  it('retries 429 (rate limit) and eventually succeeds', async () => {
    const { http, db, dlq, svc } = setup();
    db.rows = [{ id: 'B1', webhookUrl: 'https://b1/hook' }];
    http.responses.set('https://b1/hook', [{ status: 429 }, { status: 200 }]);
    await svc.processShipmentEvent(makeMessage());
    expect(http.calls.length).toBe(2);
    expect(dlq.entries.length).toBe(0);
  });
});

describe('observability', () => {
  it('logs webhook_delivered with eventId, brokerId, attempt, latencyMs', async () => {
    const { db, log, svc } = setup();
    db.rows = [{ id: 'B1', webhookUrl: 'https://b1/hook' }];
    await svc.processShipmentEvent(makeMessage());
    const delivered = log.events.find(e => e.msg === 'webhook_delivered');
    expect(delivered).toBeDefined();
    expect(delivered!.ctx).toMatchObject({
      eventId: 'shipment-events:0:100',
      brokerId: 'B1',
      attempt: 1,
    });
    expect(typeof delivered!.ctx.latencyMs).toBe('number');
  });
});

describe('input validation and parameterized SQL', () => {
  it('parks malformed JSON to DLQ and does not crash the consumer', async () => {
    const { dlq, svc } = setup();
    const bad: KafkaMessage = {
      topic: 'shipment-events', partition: 0, offset: '99',
      value: Buffer.from('not json at all'),
    };
    await svc.processShipmentEvent(bad);
    expect(dlq.entries[0].reason).toBe('payload_invalid');
  });

  it('parameterizes the broker subscription query (no string interpolation)', async () => {
    const { db, svc } = setup();
    db.rows = [];
    await svc.processShipmentEvent(makeMessage('L-EVIL; DROP TABLE--'));
    expect(db.lastSql).not.toContain('L-EVIL');
    expect(db.lastSql).toContain('$1');
    expect(db.lastParams).toEqual(['L-EVIL; DROP TABLE--']);
  });
});
