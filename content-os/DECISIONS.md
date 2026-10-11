# Jesus Replies — decisions and authorizations

Authority comes only from Selvin's own chat messages. Newest last.

| id | date | decision | source |
|----|------|----------|--------|
| DEC-JR-001 | 2026-10-03 | Test slots 08:00 and 20:30 IST, same slot on Instagram and YouTube | Selvin in chat |
| DEC-JR-002 | 2026-10-03 18:48 IST | Standing authorization for the weekly loop: "Keep the weekly batch -> scheduling -> publication -> analytics -> next-week learning loop autonomous." | config/content-os.json autonomy.standing_authorization |
| DEC-JR-003 | 2026-10-05 | QA-passed episodes go straight to the queue (Selvin: "continue") | config/content-os.json autonomy.auto_queue_on_qa_pass |
| DEC-JR-004 | 2026-10-05 | NEEDS_GENERATION slots keep their reserved id and schedule once it passes QA (referred to as DEC-018 in older files) | weekly authorization.json |
| DEC-JR-005 | 2026-10-11 20:48 IST | **Full autonomy, human gate removed.** Quote: "dont stop it continus complete automous running system i wnat it bi-weelky review it and enhance the content and enagament , qually and follow ups and crack chnaging algorthim of thsoe social medias build life long running system self correction , feeadbackloop system" | config/content-os.json autonomy.full_autonomy; config/publishing-rules.json require_human_approval=false |

## DEC-JR-005 in practice

- An episode that passes every automated gate (NIV verse verbatim check, originality, render
  QA, package QA, hosted-asset check, Buffer draft read-back) is APPROVED under the standing
  authorization and scheduled into its reserved slot on Instagram and YouTube by the content
  OS distributor. No gate was removed except the human one.
- `jr-daily-generate.yml` runs daily at 05:00 IST and prepares reserved episodes for slots up
  to 3 days ahead, then authored spares.
- Self-correction: failed episodes get bounded automatic repairs (max 3): verse wording
  re-synced to the NIV source, broken renders re-rendered, package fixes (hashtag count,
  title length, missing reference), transient hosting/Buffer retries. Unrepairable ones are
  marked exhausted and their slot is filled from READY spares; the plan is re-hashed and
  re-authorised under this decision (previous authorizations kept in
  `authorization-history.json`).
- Feedback loop: Buffer analytics -> `content-os/learnings.json` -> STRATEGY.md auto block ->
  every new brief. Bi-weekly review on even ISO weeks.
- Limits: never spends money, never changes the Buffer plan, never deletes a published post,
  held episodes (JR-0035, JR-0036) stay held.
