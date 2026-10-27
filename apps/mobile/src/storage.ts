export interface KeyStore {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  removeItem(key: string): Promise<void>;
}

// A small encrypted-value adapter. The index is committed last; failed writes
// never expose a partially written session/cache. All operations are serialized.
export function chunkedStore(raw: KeyStore): KeyStore {
  let queue: Promise<unknown> = Promise.resolve();
  function serial<T>(operation: () => Promise<T>): Promise<T> {
    const task = queue.then(operation, operation);
    queue = task.catch(() => undefined);
    return task;
  }
  async function index(
    key: string,
  ): Promise<{ generation: string; count: number } | null> {
    const value = await raw.getItem(key);
    if (!value) return null;
    const parsed: unknown = JSON.parse(value);
    if (
      !parsed ||
      typeof parsed !== 'object' ||
      !('count' in parsed) ||
      !('generation' in parsed) ||
      typeof parsed.generation !== 'string' ||
      !/^[a-z0-9]+$/.test(parsed.generation) ||
      typeof parsed.count !== 'number' ||
      !Number.isInteger(parsed.count) ||
      parsed.count < 1 ||
      parsed.count > 128
    )
      return null;
    return { count: parsed.count, generation: parsed.generation };
  }
  async function erase(key: string, old: Awaited<ReturnType<typeof index>>) {
    if (old)
      for (let i = 0; i < old.count; i++)
        await raw.removeItem(`${key}.${old.generation}.${i}`);
  }
  return {
    getItem: (key) =>
      serial(async () => {
        const meta = await index(key);
        if (!meta) return null;
        let result = '';
        for (let i = 0; i < meta.count; i++) {
          const value = await raw.getItem(`${key}.${meta.generation}.${i}`);
          if (value === null) return null;
          result += value;
        }
        return result;
      }),
    setItem: (key, value) =>
      serial(async () => {
        if (value.length > 51200)
          throw new Error('Device storage limit reached');
        const old = await index(key);
        const generation =
          Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
        const count = Math.max(1, Math.ceil(value.length / 400));
        try {
          for (let i = 0; i < count; i++)
            await raw.setItem(
              `${key}.${generation}.${i}`,
              value.slice(i * 400, (i + 1) * 400),
            );
          await raw.setItem(key, JSON.stringify({ generation, count }));
        } catch (error) {
          await erase(key, { generation, count });
          throw error;
        }
        await erase(key, old);
      }),
    removeItem: (key) =>
      serial(async () => {
        const old = await index(key);
        await raw.removeItem(key);
        await erase(key, old);
      }),
  };
}

export function memoryStore(): KeyStore {
  const values = new Map<string, string>();
  return {
    getItem: async (key) => values.get(key) ?? null,
    setItem: async (key, value) => {
      values.set(key, value);
    },
    removeItem: async (key) => {
      values.delete(key);
    },
  };
}
