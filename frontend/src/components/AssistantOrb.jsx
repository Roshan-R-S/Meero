import ThreeOrb from "./ThreeOrb";

export default function AssistantOrb({ state, sentiment }) {
  return (
    <div className="w-full h-full max-h-[280px] sm:max-h-[420px] md:max-h-[560px]">
      <ThreeOrb state={state} sentiment={sentiment} />
    </div>
  );
}
