import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");

describe("frontend style system compatibility", () => {
  it("keeps Tailwind theme colors as raw CSS variables", () => {
    const config = fs.readFileSync(path.join(root, "tailwind.config.ts"), "utf8");

    expect(config).not.toMatch(/hsl\(var\(--(?:background|foreground|primary|secondary|accent|destructive|sidebar)/);
    expect(config).toMatch(/background:\s*"var\(--background\)"/);
    expect(config).toMatch(/foreground:\s*"var\(--foreground\)"/);
    expect(config).toMatch(/card:\s*"var\(--card\)"/);
    expect(config).toMatch(/popover:\s*"var\(--popover\)"/);
    expect(config).toMatch(/DEFAULT:\s*"var\(--primary\)"/);
  });

  it("does not use Tailwind v4 shorthand class syntax in v3 source files", () => {
    const files = [
      "src/components/ui/select.tsx",
      "src/components/ui/separator.tsx",
      "src/components/ui/sheet.tsx",
      "src/components/ui/sidebar.tsx",
      "src/components/ui/tooltip.tsx",
    ];

    for (const relativePath of files) {
      const content = fs.readFileSync(path.join(root, relativePath), "utf8");

      expect(content).not.toMatch(/[a-z-]+-\(--[A-Za-z0-9_-]+\)/);
      expect(content).not.toContain("(--spacing(");
      expect(content).not.toMatch(/\bdata-open:|\bdata-closed:|\bdata-horizontal:|\bdata-vertical:/);
    }
  });
});
