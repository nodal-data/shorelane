# Stakeholder personas — revenue tie-breakers

When someone at Shorelane says "revenue," which measure they mean depends on who
they are. This mapping is the human-confirmed tie-breaker an agent should apply.

| Persona | Role | "Revenue" means | Why |
|---|---|---|---|
| Dana (CFO) | Finance | `recognized_revenue` | Board reporting and GAAP. The official number. |
| Marcus (VP Marketing) | Marketing | `gmv` | Tracks platform scale incl. marketplace gross. |
| Priya (Head of FP&A) | FP&A | `billed_revenue` | Bookings/forecast view; cares about what's invoiced. |
| Theo (Controller) | Treasury | `collected_cash` | Cash position, AR aging, bad debt. |
| Sam (COO) | Ops | `net_revenue` | Operating top line excl. marketplace pass-through. |

Default when persona is unknown: `recognized_revenue` (the CFO's number), stated
as an explicit assumption — never silently.

These personas also seed realistic eval prompts ("Dana asked what Q1 revenue was"
should resolve to recognized; "Marcus wants the revenue chart for the QBR" to GMV).
