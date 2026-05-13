import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryManagerPanel } from "./MemoryManagerPanel";
import { createMockFetch } from "../../test-utils/mockApi";

describe("MemoryManagerPanel", () => {
  it("loads memory entries and adds a new key/value pair through the explicit form", async () => {
    const { fetchMock } = createMockFetch({
      customers: [],
      providers: {},
      sessions: [],
      memory: [
        { key: "preferred_channel", value: "email", created_at: "2026-05-01T00:00:00Z" },
      ],
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<MemoryManagerPanel activeCustomerId={1} onDirtyChange={() => {}} />);

    expect(await screen.findByText("preferred_channel")).toBeInTheDocument();
    expect(screen.getByText("email")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Memory key"), "vip_status");
    await userEvent.type(screen.getByLabelText("Memory value"), "true");
    await userEvent.click(screen.getByRole("button", { name: "Add Entry" }));

    expect(await screen.findByText("vip_status")).toBeInTheDocument();
    expect(screen.getByText("true")).toBeInTheDocument();
    expect(screen.getByLabelText("Memory key")).toHaveValue("");
    expect(screen.getByLabelText("Memory value")).toHaveValue("");
  });

  it("edits an existing value in row edit mode while keeping the key stable", async () => {
    const { fetchMock } = createMockFetch({
      customers: [],
      providers: {},
      sessions: [],
      memory: [
        { key: "preferred_channel", value: "email", created_at: "2026-05-01T00:00:00Z" },
      ],
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<MemoryManagerPanel activeCustomerId={1} onDirtyChange={() => {}} />);

    expect(await screen.findByText("preferred_channel")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Edit preferred_channel" }));

    expect(screen.getByText("preferred_channel")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("preferred_channel")).not.toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText("Edit memory value for preferred_channel"));
    await userEvent.type(screen.getByLabelText("Edit memory value for preferred_channel"), "sms");
    await userEvent.click(screen.getByRole("button", { name: "Save preferred_channel" }));

    expect(await screen.findByText("sms")).toBeInTheDocument();
    expect(screen.queryByText("email")).not.toBeInTheDocument();
  });

  it("deletes an entry only after confirmation", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const { fetchMock } = createMockFetch({
      customers: [],
      providers: {},
      sessions: [],
      memory: [
        { key: "preferred_channel", value: "email", created_at: "2026-05-01T00:00:00Z" },
      ],
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<MemoryManagerPanel activeCustomerId={1} onDirtyChange={() => {}} />);

    expect(await screen.findByText("preferred_channel")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Delete preferred_channel" }));

    expect(confirmSpy).toHaveBeenCalled();
    expect(screen.queryByText("preferred_channel")).not.toBeInTheDocument();
    expect(screen.getByText("No memory entries for the active customer.")).toBeInTheDocument();
  });
});
