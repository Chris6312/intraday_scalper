import type { ExecutionBroker, ExecutionMode, MarketDataProvider } from "./enums";

export interface RuntimeSources {
  marketData: MarketDataProvider;
  execution: ExecutionBroker;
  mode: ExecutionMode;
  futureBroker: "WEBULL";
}

export interface HealthResponse {
  status: "ok" | "degraded";
  apiVersion: string;
  executionMode: ExecutionMode;
  marketDataProvider: MarketDataProvider;
  executionBroker: ExecutionBroker;
  timestamp: string;
}
