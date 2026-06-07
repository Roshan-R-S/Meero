export default function ModelStatusCard({ modelStatus }) {
  return (
    <div className="grid grid-cols-2 gap-2 text-xs">
      <span className="rounded border border-cyan-400/20 px-2 py-1">
        NN: {modelStatus ? (modelStatus.neural_net?.loaded ? "loaded" : "error") : "unknown"}
      </span>
      <span className="rounded border border-cyan-400/20 px-2 py-1">
        LLM: {modelStatus ? modelStatus.gguf_llm?.status : "unknown"}
      </span>
      <span className="col-span-2 rounded border border-cyan-400/20 px-2 py-1">
        Local voice: {modelStatus?.voice?.stt?.available ? "ready" : "unavailable"}
      </span>
    </div>
  );
}
