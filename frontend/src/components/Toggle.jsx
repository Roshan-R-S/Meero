export default function Toggle({
  label,
  checked,
  onChange,
  disabled = false,
  helpText = null,
  id,
}) {
  const toggleId = id || `toggle-${label.toLowerCase().replace(/[^a-z0-9]/g, "-")}`;

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <label
          htmlFor={toggleId}
          className={`text-xs font-mono select-none transition-colors ${
            disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
          }`}
          style={{ color: "var(--th-text)" }}
        >
          {label}
        </label>
        <label
          className={`relative inline-flex items-center ${
            disabled ? "cursor-not-allowed opacity-40" : "cursor-pointer"
          }`}
        >
          <input
            id={toggleId}
            type="checkbox"
            checked={checked}
            disabled={disabled}
            onChange={(e) => onChange(e.target.checked)}
            className="sr-only peer"
          />
          <div
            className="w-11 h-6 rounded-full transition-colors bg-neutral-800 peer-checked:bg-[var(--th-primary)]"
          />
          <span
            className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5"
          />
        </label>
      </div>
      {helpText && (
        <span className="font-mono text-[9px] text-amber-400/80 pl-0.5">
          {helpText}
        </span>
      )}
    </div>
  );
}
