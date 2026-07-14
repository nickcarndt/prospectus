"use client";

import { ArrowUp } from "lucide-react";
import { useState, type FormEvent, type KeyboardEvent } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

type QueryInputProps = {
  onSubmit: (query: string) => void;
  disabled?: boolean;
  initialValue?: string;
};

/**
 * Prominent research query input — Perplexity-grade, not a chat box.
 */
export function QueryInput({
  onSubmit,
  disabled,
  initialValue = "",
}: QueryInputProps) {
  const [value, setValue] = useState(initialValue);

  function handleSubmit(event?: FormEvent) {
    event?.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative rounded-[6px] border border-border bg-surface transition-[border-color,box-shadow] focus-within:border-primary focus-within:shadow-[0_0_0_3px_var(--accent-subtle)]">
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          placeholder="Ask a question across SEC 10-K / 10-Q filings…"
          rows={2}
          className="min-h-[72px] resize-none border-0 bg-transparent px-4 py-3.5 pr-14 text-[15px] leading-[1.6] text-ink shadow-none placeholder:text-ink-subtle focus-visible:ring-0"
        />
        <Button
          type="submit"
          size="icon"
          disabled={disabled || !value.trim()}
          className="absolute right-2.5 bottom-2.5 size-8 rounded-[6px] bg-primary text-primary-foreground hover:bg-[var(--accent-hover)]"
          aria-label="Submit query"
        >
          <ArrowUp className="size-4" />
        </Button>
      </div>
      <p className="mt-2 text-[12px] text-ink-subtle">
        Enter to search filings · Shift+Enter for newline · cited answers are
        opt-in
      </p>
    </form>
  );
}
