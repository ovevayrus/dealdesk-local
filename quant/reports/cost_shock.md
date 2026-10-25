# Cost shock result

Simulated risk demonstration on synthetic data. Not a claim of realized savings.

## Demo quote Q-1001 (100 units, $160,000 list)

| | Feed v1 | Feed v2 |
|---|---:|---:|
| Base cost | 90000.00 | 90000.00 |
| Stress cost | 97600.00 | 105600.00 |
| Economic floor (25% stress margin) | 130133.34 | 140800.00 |
| Standard offer (rep, 10%) | 144000.00 | 144000.00 |
| $136,000 concession stress margin | 28.24% | 22.35% |
| $136,000 concession status | requires_director_approval | blocked_below_floor |

Break even: at $136,000 the quote stays within policy while hardware stress cost is at most $704.00 per unit. Feed v2 sets it to $740.

## Watcher run over the five open quotes

Checked 5: 2 breach, 2 info, 1 unaffected (Q-1004). Rerunning on an unchanged feed emits no events.

### Q-1001 (breach)

Quote Q-1001 v1 at 136000.00: stress cost moved from 97600.00 to 105600.00 (hardware_unit:EDGE-100; 2026-11). Stress margin 28.24% -> 22.35%. Below the 25.00% policy minimum. New economic floor 140800.00. The sent offer and its approval are unchanged; revised terms need a new quote version and a fresh approval.

* Reprice to 140800.00 (+4800.00), discount 12.00%, needs director approval.
* Phase: commit 50 units at 72000.00, stress margin 26.67%, within rep authority.
* Keep 136000.00 with a cost adjustment clause above 704.00 per unit (finance and legal review).

### Q-1002 (info)

Quote Q-1002 v1 at 144000.00: stress cost moved from 97600.00 to 105600.00 (hardware_unit:EDGE-100; 2026-11). Stress margin 32.22% -> 26.67%.

### Q-1003 (info)

Quote Q-1003 v1 at 76000.00: stress cost moved from 48800.00 to 52800.00 (hardware_unit:EDGE-100; 2026-12). Stress margin 35.79% -> 30.53%.

### Q-1005 (breach)

Quote Q-1005 v1 at 104960.00: stress cost moved from 78560.00 to 84960.00 (hardware_unit:EDGE-100; 2026-12). Stress margin 25.15% -> 19.05%. Below the 25.00% policy minimum. New economic floor 113280.00. The sent offer and its approval are unchanged; revised terms need a new quote version and a fresh approval.

* Reprice to 113280.00 (+8320.00), discount 11.50%, needs director approval.
* Phase: commit 40 units at 57600.00, stress margin 26.25%, within rep authority.
* Keep 104960.00 with a cost adjustment clause above 662.00 per unit (finance and legal review).
