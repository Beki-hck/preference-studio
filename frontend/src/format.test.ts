import { describe, expect, it } from "vitest";
import { agreementLabel, pct, splitBlocks } from "./format";

describe("splitBlocks", () => {
  it("separates text and fenced code", () => {
    expect(splitBlocks("Use this:\n```python\nprint(1)\n```\nDone.")).toEqual([
      { kind: "text", text: "Use this:" },
      { kind: "code", lang: "python", text: "print(1)" },
      { kind: "text", text: "Done." },
    ]);
  });
  it("handles plain text and unclosed fences", () => {
    expect(splitBlocks("hello")).toEqual([{ kind: "text", text: "hello" }]);
    expect(splitBlocks("```\nx = 1")).toEqual([{ kind: "code", lang: undefined, text: "x = 1" }]);
  });
});

describe("formatting", () => {
  it("formats percentages and agreement bands", () => {
    expect(pct(0.756)).toBe("76%");
    expect(pct(null)).toBe("n/a");
    expect(agreementLabel(0.21)).toBe("fair");
    expect(agreementLabel(0.85)).toBe("almost perfect");
    expect(agreementLabel(-0.1)).toBe("worse than chance");
  });
});
