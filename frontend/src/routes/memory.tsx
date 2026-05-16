import { useState, useEffect } from "react";
import type { FormEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getCustomers, getMemory, putMemory, deleteMemoryEntry } from "@/lib/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { CustomerMemoryRecord } from "@/lib/types";

type DialogMode =
  | { type: "closed" }
  | { type: "add" }
  | { type: "edit"; entry: CustomerMemoryRecord }
  | { type: "delete"; entry: CustomerMemoryRecord };

export function MemoryPage() {
  const [selectedCustomerId, setSelectedCustomerId] = useState<number | null>(null);
  const [dialog, setDialog] = useState<DialogMode>({ type: "closed" });
  const [addKey, setAddKey] = useState("");
  const [addValue, setAddValue] = useState("");
  const [editValue, setEditValue] = useState("");

  const queryClient = useQueryClient();

  const { data: customers = [] } = useQuery({
    queryKey: ["customers"],
    queryFn: getCustomers,
  });

  useEffect(() => {
    if (selectedCustomerId === null && customers.length > 0) {
      setSelectedCustomerId(customers[0].customer_id);
    }
  }, [customers, selectedCustomerId]);

  const { data: entries = [] } = useQuery({
    queryKey: ["memory", selectedCustomerId],
    queryFn: () => getMemory(selectedCustomerId!),
    enabled: selectedCustomerId !== null,
  });

  const putMutation = useMutation({
    mutationFn: (vars: { key: string; value: string }) =>
      putMemory(selectedCustomerId!, [vars]),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["memory", selectedCustomerId] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (key: string) => deleteMemoryEntry(selectedCustomerId!, key),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["memory", selectedCustomerId] }),
  });

  function handleAddSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const key = addKey.trim();
    const value = addValue.trim();
    if (!key || !value) return;
    putMutation.mutate({ key, value }, {
      onSuccess: () => {
        setDialog({ type: "closed" });
        setAddKey("");
        setAddValue("");
      },
    });
  }

  function handleEditSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (dialog.type !== "edit") return;
    putMutation.mutate({ key: dialog.entry.key, value: editValue }, {
      onSuccess: () => setDialog({ type: "closed" }),
    });
  }

  function handleDeleteConfirm() {
    if (dialog.type !== "delete") return;
    deleteMutation.mutate(dialog.entry.key, {
      onSuccess: () => setDialog({ type: "closed" }),
    });
  }

  function openEditDialog(entry: CustomerMemoryRecord) {
    setEditValue(entry.value);
    setDialog({ type: "edit", entry });
  }

  return (
    <div className="flex flex-col gap-6 p-6 overflow-y-auto h-full">
      <div>
        <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Manager</p>
        <h1 className="text-2xl font-bold">Memory Manager</h1>
      </div>

      <div className="flex items-center gap-3">
        <label htmlFor="customer-select" className="text-sm font-medium shrink-0">
          Customer
        </label>
        <Select
          value={selectedCustomerId !== null ? String(selectedCustomerId) : ""}
          onValueChange={(v) => setSelectedCustomerId(Number(v))}
        >
          <SelectTrigger
            id="customer-select"
            aria-label="Customer"
            className="w-56"
          >
            <SelectValue placeholder="Select customer…" />
          </SelectTrigger>
          <SelectContent>
            {customers.map((c) => (
              <SelectItem key={c.customer_id} value={String(c.customer_id)}>
                {c.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          disabled={selectedCustomerId === null}
          onClick={() => setDialog({ type: "add" })}
        >
          Add Entry
        </Button>
      </div>

      {selectedCustomerId === null ? (
        <p className="text-sm text-muted-foreground">
          Select a customer to view memory entries.
        </p>
      ) : entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No memory entries for this customer.
        </p>
      ) : (
        <div className="rounded-none border border-border/70">
          <Table className="table-fixed">
            <TableHeader>
              <TableRow>
                <TableHead className="w-[28%]">Key</TableHead>
                <TableHead className="w-[40%]">Value</TableHead>
                <TableHead className="w-[16%]">Created At</TableHead>
                <TableHead className="w-[16%]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.map((entry) => (
                <TableRow key={entry.key}>
                  <TableCell className="font-mono whitespace-normal break-words align-top">{entry.key}</TableCell>
                  <TableCell className="whitespace-normal break-words align-top">{entry.value}</TableCell>
                  <TableCell className="text-muted-foreground align-top">
                    {new Date(entry.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openEditDialog(entry)}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setDialog({ type: "delete", entry })}
                      >
                        Delete
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Add Entry Dialog */}
      <Dialog
        open={dialog.type === "add"}
        onOpenChange={(open) => { if (!open) setDialog({ type: "closed" }); }}
      >
        <DialogContent aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle>Add Memory Entry</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleAddSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="add-key" className="text-sm font-medium">Key</label>
              <Input
                id="add-key"
                value={addKey}
                onChange={(e) => setAddKey(e.target.value)}
                placeholder="e.g. preferred_channel"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="add-value" className="text-sm font-medium">Value</label>
              <Textarea
                id="add-value"
                value={addValue}
                onChange={(e) => setAddValue(e.target.value)}
                placeholder="e.g. email"
                rows={3}
              />
            </div>
            <DialogFooter>
              <Button type="submit" disabled={putMutation.isPending}>
                Save
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog
        open={dialog.type === "edit"}
        onOpenChange={(open) => { if (!open) setDialog({ type: "closed" }); }}
      >
        <DialogContent aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle>Edit Memory Entry</DialogTitle>
          </DialogHeader>
          {dialog.type === "edit" && (
            <form onSubmit={handleEditSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <p className="text-sm font-medium">Key</p>
                <p className="font-mono text-sm text-muted-foreground">{dialog.entry.key}</p>
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="edit-value" className="text-sm font-medium">Value</label>
                <Textarea
                  id="edit-value"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  rows={3}
                />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={putMutation.isPending}>
                  Save
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={dialog.type === "delete"}
        onOpenChange={(open) => { if (!open) setDialog({ type: "closed" }); }}
      >
        <DialogContent aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle>Delete Memory Entry</DialogTitle>
          </DialogHeader>
          {dialog.type === "delete" && (
            <>
              <p className="text-sm">
                Are you sure you want to delete &ldquo;{dialog.entry.key}&rdquo;? This action cannot be
                undone.
              </p>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setDialog({ type: "closed" })}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleDeleteConfirm}
                  disabled={deleteMutation.isPending}
                >
                  Delete
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
