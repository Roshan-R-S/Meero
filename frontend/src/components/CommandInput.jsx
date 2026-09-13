import { Send } from "lucide-react";

export default function CommandInput({
  disabled,
  onSubmit,
  setTypedCommand,
  typedCommand,
}) {
  return (
    <form
      onSubmit={onSubmit}
      className="flex items-center gap-2 w-[min(20rem,80vw)] rounded-full bg-black/45 border px-3 py-2 backdrop-blur transition-all"
      style={{
        borderColor: "var(--th-border)",
        boxShadow: "0 0 24px var(--th-primary-subtle)",
      }}
    >
      <input
        value={typedCommand}
        onChange={(event) => setTypedCommand(event.target.value)}
        aria-label="Type command"
        placeholder="Type a command"
        disabled={disabled}
        className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:opacity-40"
        style={{ color: "var(--th-text)" }}
      />
      <button
        type="submit"
        aria-label="Send command"
        disabled={!typedCommand.trim() || disabled}
        className="grid h-8 w-8 place-items-center rounded-full text-white transition hover:brightness-110 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
        style={{ background: "var(--th-primary)" }}
      >
        <Send size={16} />
      </button>
    </form>
  );
}
