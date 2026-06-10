export default function StatusBanner({ serverReachable, notice, onRetry }) {
  if (!serverReachable) {
    return (
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-60 rounded bg-red-700/90 px-4 py-2 text-sm text-white shadow">
        Server unreachable - <button onClick={onRetry} className="underline">Retry</button>
      </div>
    );
  }
  if (!notice) return null;
  return <div className="absolute top-4 left-1/2 -translate-x-1/2 z-60 text-xs text-yellow-200">{notice}</div>;
}
