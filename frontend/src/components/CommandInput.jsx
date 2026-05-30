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
      className="flex items-center gap-2 w-[min(20rem,80vw)] rounded-full bg-black/45 border border-cyan-400/25 px-3 py-2 shadow-[0_0_24px_rgba(8,145,178,0.16)] backdrop-blur"
    >
      <input
        value={typedCommand}
        onChange={(event) => setTypedCommand(event.target.value)}
        aria-label="Type command"
        placeholder="Type a command"
        disabled={disabled}
        className="min-w-0 flex-1 bg-transparent text-sm text-cyan-50 placeholder:text-cyan-200/40 outline-none"
      />
      <button
        type="submit"
        aria-label="Send command"
        disabled={!typedCommand.trim() || disabled}
        className="grid h-8 w-8 place-items-center rounded-full bg-cyan-600/90 text-white transition hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <Send size={16} />
      </button>
    </form>
  );
}
