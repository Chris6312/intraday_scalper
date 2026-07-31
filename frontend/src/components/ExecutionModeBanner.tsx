import type { RuntimeSources } from "../domain/contracts";

interface Props {
  sources: RuntimeSources;
}

export function ExecutionModeBanner({ sources }: Props) {
  return (
    <header className="mode-banner" aria-label="Execution sources">
      <strong>Mode: {sources.mode}</strong>
      <span>Market Data: {sources.marketData}</span>
      <span>Execution: {sources.execution.replace("_", " ")}</span>
      <span>Future Broker: {sources.futureBroker}</span>
    </header>
  );
}
