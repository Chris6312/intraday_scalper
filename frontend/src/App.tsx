import { ExecutionModeBanner } from "./components/ExecutionModeBanner";
import type { RuntimeSources } from "./domain/contracts";

const approvedSources: RuntimeSources = {
  marketData: "PUBLIC",
  execution: "INTERNAL_PAPER",
  mode: "PAPER",
  futureBroker: "WEBULL",
};

export default function App() {
  return (
    <main>
      <ExecutionModeBanner sources={approvedSources} />
      <section className="shell">
        <p className="eyebrow">PHASE 0 FOUNDATION</p>
        <h1>Options Intraday Scalper</h1>
        <p>
          The broker-neutral contracts, safety defaults, API version, and project scaffolding are
          active. Trading logic is not enabled in Phase 0.
        </p>
      </section>
    </main>
  );
}
