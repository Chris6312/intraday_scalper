# Order State Machine Foundation

Approved states:

```text
CREATED -> RESERVED -> SUBMITTED -> WORKING
WORKING -> PARTIALLY_FILLED -> FILLED
WORKING -> REPLACED -> WORKING
WORKING/PARTIALLY_FILLED -> CANCEL_REQUESTED -> CANCELED
CREATED/RESERVED/SUBMITTED/WORKING -> REJECTED
WORKING/PARTIALLY_FILLED -> EXPIRED
```

Invalid transitions must be rejected and written to the audit log. The ledger stores every transition as an immutable event; the current order row is a projection for efficient reads.
