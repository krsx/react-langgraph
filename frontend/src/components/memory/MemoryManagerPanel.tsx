import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { deleteMemoryEntry, getMemory, putMemory } from "../../lib/api";
import type { CustomerMemoryRecord } from "../../lib/types";
import { Button } from "../ui/button";

type MemoryManagerPanelProps = {
  activeCustomerId: number | null;
  onDirtyChange: (dirty: boolean) => void;
};

export function MemoryManagerPanel({
  activeCustomerId,
  onDirtyChange,
}: MemoryManagerPanelProps) {
  const [entries, setEntries] = useState<CustomerMemoryRecord[]>([]);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editingOriginalValue, setEditingOriginalValue] = useState("");
  const [editingValue, setEditingValue] = useState("");
  const [keyInput, setKeyInput] = useState("");
  const [valueInput, setValueInput] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (activeCustomerId === null) {
        setEntries([]);
        return;
      }

      const nextEntries = await getMemory(activeCustomerId);
      if (!cancelled) {
        setEntries(nextEntries);
        setEditingKey(null);
        setEditingOriginalValue("");
        setEditingValue("");
        setKeyInput("");
        setValueInput("");
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [activeCustomerId]);

  useEffect(() => {
    const addFormDirty = keyInput.trim().length > 0 || valueInput.trim().length > 0;
    const editFormDirty = editingKey !== null && editingValue !== editingOriginalValue;
    onDirtyChange(addFormDirty || editFormDirty);
  }, [editingKey, editingOriginalValue, editingValue, keyInput, onDirtyChange, valueInput]);

  async function handleAddEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (activeCustomerId === null) {
      return;
    }

    const nextKey = keyInput.trim();
    const nextValue = valueInput.trim();
    if (!nextKey || !nextValue) {
      return;
    }

    await putMemory(activeCustomerId, [{ key: nextKey, value: nextValue }]);
    setEntries((current) => [
      ...current,
      {
        key: nextKey,
        value: nextValue,
        created_at: "2026-05-01T00:00:00Z",
      },
    ]);
    setKeyInput("");
    setValueInput("");
  }

  function startEditing(entry: CustomerMemoryRecord) {
    setEditingKey(entry.key);
    setEditingOriginalValue(entry.value);
    setEditingValue(entry.value);
  }

  function cancelEditing() {
    setEditingKey(null);
    setEditingOriginalValue("");
    setEditingValue("");
  }

  async function saveEditing(key: string) {
    if (activeCustomerId === null) {
      return;
    }

    await putMemory(activeCustomerId, [{ key, value: editingValue }]);
    setEntries((current) =>
      current.map((entry) => (entry.key === key ? { ...entry, value: editingValue } : entry)),
    );
    cancelEditing();
  }

  async function handleDelete(key: string) {
    if (activeCustomerId === null) {
      return;
    }

    if (!window.confirm(`Delete memory entry "${key}"?`)) {
      return;
    }

    await deleteMemoryEntry(activeCustomerId, key);
    setEntries((current) => current.filter((entry) => entry.key !== key));
    if (editingKey === key) {
      cancelEditing();
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Right Panel</p>
        <h2 className="text-xl font-bold">Memory Manager</h2>
      </div>

      <form className="space-y-3 rounded-[24px] border border-border/70 bg-background/80 p-4 shadow-sm" onSubmit={handleAddEntry}>
        <div>
          <label className="text-sm font-medium" htmlFor="memory-key">
            Memory key
          </label>
          <input
            id="memory-key"
            className="mt-2 w-full rounded-2xl border border-border bg-card px-3 py-2 text-sm"
            value={keyInput}
            onChange={(event) => setKeyInput(event.target.value)}
          />
        </div>

        <div>
          <label className="text-sm font-medium" htmlFor="memory-value">
            Memory value
          </label>
          <textarea
            id="memory-value"
            className="mt-2 min-h-24 w-full rounded-2xl border border-border bg-card px-3 py-2 text-sm"
            value={valueInput}
            onChange={(event) => setValueInput(event.target.value)}
          />
        </div>

        <Button type="submit">Add Entry</Button>
      </form>

      <section className="rounded-[24px] border border-border/70 bg-background/80 p-4 shadow-sm">
        <h3 className="text-lg font-bold">Entries</h3>
        <div className="mt-4 space-y-2">
          {entries.length === 0 ? (
            <p className="text-sm text-muted-foreground">No memory entries for the active customer.</p>
          ) : (
            entries.map((entry) => (
              <article key={entry.key} className="rounded-2xl bg-card px-3 py-3">
                <p className="font-medium">{entry.key}</p>
                {editingKey === entry.key ? (
                  <div className="mt-3 space-y-3">
                    <textarea
                      aria-label={`Edit memory value for ${entry.key}`}
                      className="min-h-24 w-full rounded-2xl border border-border bg-background px-3 py-2 text-sm"
                      value={editingValue}
                      onChange={(event) => setEditingValue(event.target.value)}
                    />
                    <div className="flex flex-wrap gap-2">
                      <Button type="button" onClick={() => void saveEditing(entry.key)}>
                        {`Save ${entry.key}`}
                      </Button>
                      <Button type="button" variant="outline" onClick={cancelEditing}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="mt-3">
                    <p className="text-sm text-muted-foreground">{entry.value}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Button type="button" variant="outline" onClick={() => startEditing(entry)}>
                        {`Edit ${entry.key}`}
                      </Button>
                      <Button type="button" variant="outline" onClick={() => void handleDelete(entry.key)}>
                        {`Delete ${entry.key}`}
                      </Button>
                    </div>
                  </div>
                )}
              </article>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
