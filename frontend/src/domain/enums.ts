export type ExecutionMode = "PAPER" | "SHADOW" | "APPROVAL" | "LIVE";
export type MarketDataProvider = "PUBLIC";
export type ExecutionBroker = "INTERNAL_PAPER" | "ALPACA_PAPER" | "WEBULL";

export type OrderState =
  | "CREATED"
  | "RESERVED"
  | "SUBMITTED"
  | "WORKING"
  | "PARTIALLY_FILLED"
  | "REPLACED"
  | "FILLED"
  | "CANCEL_REQUESTED"
  | "CANCELED"
  | "REJECTED"
  | "EXPIRED";
