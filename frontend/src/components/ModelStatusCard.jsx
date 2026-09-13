export default function ModelStatusCard({ modelStatus }) {
  return (
    <div className="grid grid-cols-2 gap-2 text-xs">
      <span className="rounded border px-2 py-1" style={{ borderColor: "var(--th-border)" }}>
        NN: {modelStatus ? (modelStatus.neural_net?.loaded ? "loaded" : "error") : "unknown"}
      </span>
      <span className="rounded border px-2 py-1" style={{ borderColor: "var(--th-border)" }}>
        LLM: {modelStatus ? modelStatus.gguf_llm?.status : "unknown"}
      </span>
      <span className="col-span-2 rounded border px-2 py-1" style={{ borderColor: "var(--th-border)" }}>
        Local voice: {modelStatus?.voice?.stt?.available ? "ready" : "unavailable"}
      </span>
    </div>
  );
}
