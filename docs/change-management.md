# Change-management plan — close cockpit rollout

The tool is the easy part. This plan is about the people whose month-end is going to be measured for the first time.

**The central risk, stated plainly:** this cockpit makes one entity's underperformance visible to the group. NS30 closes in 8.2 working days against a group average of 5.3, posts 22 % of entries by hand against 13 %, and is late on 9 % of postings against 2 %. Those numbers are correct, and they are about a team of people who will read them.

A rollout that treats that as a reporting detail will produce gaming, not improvement. The entity will start closing the checklist on time and posting afterwards, and every number in the cockpit will improve while nothing real changes.

---

## Stakeholders

| Stakeholder | Interest | Stance to expect | How to handle |
|---|---|---|---|
| **CFO** | Faster close, fewer surprises | Sponsor | Wants one number per page. Give the trend, not the detail |
| **Group Close Manager** | Sees problems during the close, not after | Champion | Primary user. Co-design the close-monitor page with them |
| **Head of Programme Controlling** | Early warning on overruns | Champion | The EAC is their argument in a steering meeting. Make its limitations explicit or it gets used as a forecast |
| **Entity Finance Managers** ×4 | Being measured against each other | **Mixed — and the one that decides the outcome** | See below |
| **Entity closing teams** | More scrutiny, no more resource | Sceptical | They are not the problem; the process is. Say so and mean it |
| **Group Consolidation** | Fewer intercompany chases | Supportive | Quick win: five open items instead of a mailbox |
| **IT / BI team** | Another system | Neutral | Runs on existing platform skills. No new operational burden |
| **Works council / HR** | Individual performance measurement | **Must be engaged before launch** | See *Not a performance tool* |

### The entity finance managers

Three will be comfortable — their numbers are good. One will not, and how that conversation goes decides whether the rollout works.

The wrong approach is to launch group-wide and let the ranking speak. The right one is to **show the slow entity its own data first, privately, before anyone else sees it**, and ask what it explains. Two outcomes, both useful:

- They already know, and the cockpit gives them evidence to ask for resource or process change. They become the strongest advocate, because the tool finally makes their case for them.
- They do not know, and it is a genuine finding — in which case the manual-posting share tells them where to look.

Either way they must not first encounter it on a slide in front of their peers.

---

## Communication plan

| When | Audience | Message | Channel |
|---|---|---|---|
| −6 weeks | CFO, Close Manager | What it will show, including that entities will be comparable | Working session |
| −5 weeks | Slow entity's manager, **alone** | Their own data, before anyone else sees it | 1:1 |
| −4 weeks | All entity managers | Purpose, what is measured, what is **not** | Working session |
| −3 weeks | Works council / HR | Confirmation that no individual is measured or identifiable | Formal briefing |
| −2 weeks | Closing teams | Demo, and the explicit statement that this measures the process | Per-entity, 30 min |
| Launch | All | Access, champions, where to raise issues | Email + intranet |
| +1 period | All | First close reviewed together, with the group present | Review meeting |

**The message that must not be sent:** "we are now tracking how fast each entity closes." The message that works: "we are now able to see *where* the close loses time, so the argument for fixing it can be made with evidence."

---

## Not a performance tool

Non-negotiable, and stated in writing before launch:

- **No individual is identifiable.** Posting user IDs are pseudonymous tokens and do not reach the reporting layer at all — enforced in code, not by policy ([`gdpr-and-data-protection.md`](gdpr-and-data-protection.md)).
- **The unit of analysis is the entity and the process**, never a person.
- **No drill to user level exists.** Not "is restricted" — does not exist. That is a design decision precisely so it cannot be relaxed under pressure later.
- Engage the works council **before** launch, not after the first complaint.

The reason to be firm: the moment a closing clerk believes this measures them personally, they will optimise the metric. Late postings become postings dated earlier. The data quality that makes the cockpit worth having is destroyed by the fear that it measures individuals.

---

## Training

Different populations, different needs. One session for everyone is one session wrong for everyone.

| Population | Format | Focus |
|---|---|---|
| CFO, group finance | 30 min walkthrough | How to read the three pages. Not how to filter |
| Entity finance managers | 90 min hands-on | Their own data. Drill from days-to-close to the manual postings behind it |
| Closing teams | 45 min per entity | The close monitor only. What "late" means and how their cut-off is defined |
| Programme controllers | 90 min hands-on | Budget variance and the EAC, **including its limitations** |
| Champions | Half day | Everything, plus how to answer "that number looks wrong" |

**A champion in each entity's closing team.** Not IT, not a manager — someone who does the close. Questions go to them first. Two reasons: they answer in the language of the close rather than the language of the tool, and a colleague saying "that number is right, here is why" carries weight that a BI team never will.

---

## Hypercare

**Two full period closes**, because the first close is not representative — everyone is watching and behaving unusually. The second is the real test.

| Phase | Duration | Response | Focus |
|---|---|---|---|
| Close 1 | Period end → +10 wd | Same day | Daily standup during the close window |
| Close 2 | Period end → +10 wd | Next day | Weekly review |
| Steady state | From close 3 | Standard service desk | Champions handle first line |

**Exit criteria — all four, before hypercare ends:**

- No open data-quality issue where a user's number and the cockpit's disagree.
- Every champion has answered at least one question without escalating.
- At least one process change has been made *because* of something the cockpit showed. If nothing has changed, the tool is being watched, not used.
- The slow entity has agreed what its numbers mean.

---

## Adoption KPIs

Measured monthly. Adoption is a hypothesis until it has evidence.

| Metric | Target by close 3 | Why this one |
|---|---|---|
| Weekly active users | ≥ 70 % of named users | Below half means it is not in the workflow |
| Users during the close window | ≥ 90 % of closing teams | The cockpit is for *during* the close, not after |
| Ad-hoc report requests deflected | −30 % | The hard measure. If requests do not fall, it did not replace anything |
| Time to first drill | Falling | Users who only read the summary have not adopted it |
| Process changes attributed | ≥ 1 per quarter | The only one that measures value rather than usage |

**The one that matters:** report-request deflection. Everything else measures whether people opened it.

---

## What can go wrong

| Risk | Signal | Response |
|---|---|---|
| **Gaming** | Days-to-close improves while late postings do not | Cross-check the two. Improvement in one alone is a process artefact |
| Slow entity disengages | Stops attending reviews | The 1:1 at −5 weeks is the mitigation. If it fails, escalate to the CFO as a resourcing conversation, not a performance one |
| EAC used as a forecast | It appears in a steering pack as a committed number | Labelled in the model, the view header and the training. Repeat as needed |
| "The numbers are wrong" | Any disagreement with a user's own figure | Treat as real until disproved. The reconciliation exists — 24 cross-checks — but a user's spreadsheet is a legitimate second opinion |
| Champion leaves | Questions escalate again | Two champions per entity from the start |
| Novelty fades | Usage drops after close 3 | Expected. The floor matters, not the peak. Below 50 % at close 6 means it did not become part of the process |
