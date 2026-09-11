# How Cancellation Appeals Work on Cadence

A stream is supposed to make payment follow the work. But sometimes a payer has to stop a stream early. The work may have changed, the agreement may have ended, or the payer may believe the payee did not deliver what was agreed.

Cadence lets the payer cancel a stream, but cancellation is not instantly final when there is still unstreamed money left.

The payee receives everything earned up to the moment of cancellation. The remaining balance is held in escrow for a short appeal period. If the payee believes the cancellation is wrong, they can appeal it, submit evidence, discuss the facts with the payer in a Bant room, and have the case reviewed by GenLayer.

The goal is simple: the payer should be able to stop a stream, but the payee should not lose money that is still owed under an active agreement without a fair way to challenge the decision.

> [IMAGE PLACEHOLDER 1 - A cancelled stream card on the Cadence dashboard showing the cancellation reason, the escrowed balance, and the "Appeal cancellation" button.]

## What happens when a payer cancels a stream

When a payer cancels a stream, Cadence calculates how much has accrued up to that exact moment.

That earned amount is paid to the payee immediately.

The amount that has not streamed yet stays inside the PayrollManager contract. It is not sent back to the payer immediately, and it is not available for the payee to withdraw. It is held while the appeal window is open.

The cancellation also includes a reason. This gives the payee a clear explanation of why the stream was stopped and gives GenLayer something specific to evaluate if an appeal is filed.

The stream card moves into an appeal window, and the payee has 24 hours to decide whether to appeal.

This is the first important distinction:

- Money already earned goes to the payee.
- Unstreamed money stays escrowed.
- The payee gets 24 hours to challenge the cancellation.
- The payer's reason becomes part of the case record.

> [IMAGE PLACEHOLDER 2 - The cancellation confirmation modal showing the payer entering a cancellation reason before confirming.]

## Step 1: The payee opens the appeal

The appeal process starts from the payee's stream card.

During the 24-hour appeal window, the payee sees an "Appeal cancellation" button. Clicking it opens the appeal form.

The appeal is not a general complaint form. It asks one focused question:

**Why should this stream continue?**

The payee needs to explain how the cancellation conflicts with the agreement, the expected deliverables, the payment terms, or the facts of what happened.

The statement must connect the dispute to the specific stream. A general statement such as "I did the work" is not enough on its own. The appeal should explain:

- What the payer agreed to pay for.
- What the payee delivered or was still obligated to deliver.
- Why the payer's cancellation reason is incorrect or premature.
- What evidence supports the claim.
- Why the stream should resume on its original terms.

The payee also provides public evidence sources. Cadence supports sources such as:

- Agreements and statements of work.
- Work product and deliverables.
- Invoices.
- Communications between the payer and payee.
- Acceptance records.
- Payment records.
- Identity records.
- Other relevant public records.

The evidence sources must be publicly reachable over HTTPS. Cadence fetches each source and records its SHA-256 hash before the appeal is submitted. That means the evidence reviewed later must match the exact evidence that was committed when the appeal was filed.

The payee can submit between one and eight sources, and each source needs a short description explaining what it proves.

> [IMAGE PLACEHOLDER 3 - The appeal modal showing the statement field, evidence source type selector, public URL field, and "What this source proves" field.]

## Step 2: The payee signs and submits the appeal

Before the appeal is submitted, Cadence verifies that the person filing it controls the payee wallet for that stream.

The payee signs an authorization message with their wallet. This does not transfer funds. It simply confirms that the payee is the person asking Cadence to open the appeal.

Cadence then prepares an evidence package containing:

- The payee's appeal statement.
- The requested remedy: continue the stream.
- The list of evidence sources.
- The description and hash of each source.

The package is hashed and committed on Arc. The payee then confirms the `appealCancellation` transaction.

Once that transaction is confirmed, the stream moves from the appeal window into the appealed state. The escrowed balance remains locked while the case proceeds.

The appeal must be submitted within the 24-hour window. Filing at the deadline is valid. Filing after the deadline is not.

If the payee does not appeal in time, the cancellation can be finalized and the escrowed balance is returned to the payer.

> [IMAGE PLACEHOLDER 4 - The wallet confirmation screen or the Cadence appeal status showing "Confirming Arc appeal."]

## Step 3: The Bant room opens

After the appeal is confirmed on Arc, Cadence opens a Bant room for the payer and payee.

The Bant room is a short, structured evidence exchange around the disputed cancellation. It gives both sides a place to explain what happened, respond to the other side, and attach additional evidence.

The room is connected to one specific case and one specific stream. Only the payer and payee are treated as parties to the case.

The payee can:

- Explain the work that was completed.
- Respond to the cancellation reason.
- Add evidence that connects the work to the agreement.
- Clarify dates, milestones, invoices, or communications.
- Explain why the stream should resume.

The payer can:

- Explain why the stream was cancelled.
- Point to the relevant part of the agreement.
- Show that a deliverable was not completed or accepted.
- Provide communications or records supporting the cancellation.
- Clarify why the cancellation was allowed under the agreed terms.

Each message can include a public evidence URL, an evidence type, and a description of what the evidence proves.

The room is not an endless negotiation. The Bant period lasts 24 hours from the time the appeal is filed. Both sides have a limited period to provide their account and support it with records.

> [IMAGE PLACEHOLDER 5 - The Bant room showing payer and payee messages, role labels, timestamps, and attached evidence links.]

## What the Bant room is for

The Bant room exists because not every dispute can be understood from one person's initial submission.

A payee may have a signed agreement but fail to explain how it relates to the cancellation. A payer may have a valid cancellation right but leave out an important acceptance record. A message from the other party may add the missing context.

The room gives both sides the opportunity to put that context on the record.

It also makes the process less dependent on private conversations. Instead of asking one party to trust the other party's version of events, Cadence preserves a shared transcript that can be reviewed as part of the appeal.

The Bant room is not designed for abuse, threats, or unrelated arguments. The useful messages are the ones that answer the actual dispute:

- What was agreed?
- What was delivered?
- What was accepted?
- What was paid?
- What reason was given for cancellation?
- Does the evidence support or contradict that reason?

When the 24-hour Bant period ends, the room closes. The transcript is frozen and cannot be edited.

> [IMAGE PLACEHOLDER 6 - The Bant room after closing, showing the frozen transcript and the "Bant period closed" state.]

## Step 4: The case is committed to GenLayer

Once the Bant period closes, Cadence combines the original appeal package with the frozen Bant transcript.

The complete case includes:

- The Arc case ID.
- The payer and payee addresses.
- The stream ID.
- The cancellation reason.
- The rate and escrowed balance.
- The stream deliverables, if provided.
- The payee's original statement.
- The original evidence sources.
- The messages exchanged in the Bant room.
- Any evidence attached during the Bant period.

The combined record is hashed before it is sent to GenLayer. This creates a fixed evidence package for adjudication.

GenLayer does not hold the USDC and does not control the stream balance. Arc remains the source of truth for the money, the stream terms, and the deadlines.

GenLayer's role is narrower: it reviews the committed evidence and produces a verdict on whether the cancellation should stand.

## What GenLayer decides

GenLayer evaluates one specific question:

**Has the payee provided strong, coherent, verifiable evidence that the cancellation is illegitimate under a continuing agreement or is based on a material factual error, such that the stream should resume on its original terms?**

The payee carries the burden of proof.

An appeal can be upheld when the evidence shows things such as:

- A signed agreement that is still active.
- A termination notice that was required but not provided.
- Work that was completed and accepted.
- A milestone that was reached.
- Communications where the payer confirmed continuation or acceptance.
- Records showing that the payer's stated reason for cancellation is factually wrong.

An appeal will normally be rejected when it relies only on:

- The payee's unsupported statement.
- Inaccessible or private evidence.
- Files that no longer match their committed hashes.
- Screenshots with no reliable connection to the parties or stream.
- Evidence unrelated to the cancellation reason.
- Contradictory records that leave the obligation unclear.
- A disagreement with a cancellation that the payer was contractually allowed to make.

GenLayer validators review the same committed evidence and reach a binary outcome:

- Appeal upheld.
- Appeal rejected.

The verdict also includes a reason code, confidence score, summary, and findings. An upheld vote below the 70 percent confidence threshold is treated as insufficient evidence and normalized to a rejection.

This keeps the standard intentionally narrow. GenLayer is not deciding every possible legal question between the parties. It is deciding whether this cancelled stream should resume based on the evidence submitted in this case.

> [IMAGE PLACEHOLDER 7 - The Cadence appeal status showing the case waiting for GenLayer adjudication.]

## Step 5: The verdict returns to Arc

After GenLayer produces a finalized verdict, Cadence relays the result back to the PayrollManager contract on Arc.

The relay can deliver only the final appeal outcome and its verdict hash. It cannot change:

- The payer.
- The payee.
- The stream rate.
- The original stream terms.
- The amount held in escrow.
- The cancellation reason.

The Arc contract applies one of two outcomes.

### If the appeal is upheld

The cancellation does not stand.

The stream becomes active again, and the escrowed balance remains available inside the stream. The stream resumes at its original rate from the point the appeal is resolved.

The stream does not retroactively accrue new earnings for the period in which it was paused. The payee keeps everything earned before cancellation, and future earnings begin again when the stream resumes.

This gives the payee a meaningful remedy without rewriting the stream's history.

### If the appeal is rejected

The cancellation stands.

The stream remains inactive, and the escrowed unstreamed balance is released back to the payer.

The payee keeps the amount that had already accrued before the cancellation. The rejected appeal only determines what happens to the balance that had not yet streamed.

> [IMAGE PLACEHOLDER 8 - A resolved appeal showing the "Appeal upheld" outcome and the stream returning to an active state.]

> [IMAGE PLACEHOLDER 9 - A resolved appeal showing the "Cancellation upheld" outcome and the escrowed balance refunded to the payer.]

## What happens when there is no appeal

If the payee does nothing during the 24-hour appeal window, the cancellation becomes unappealed.

Anyone can call the finalization function after the deadline. Cadence then releases the unstreamed balance back to the payer and closes the cancellation lifecycle.

The payer does not need to wait indefinitely for the payee to respond. The payee gets a clear window to challenge the cancellation, and silence after that window allows the stream to settle.

## What happens if adjudication times out

Cadence also protects the payer from escrow being locked forever because of a failed relay or an unavailable adjudicator.

After the bounded adjudication timeout, the appeal can be finalized as timed out. The escrowed balance is returned to the payer.

This does not mean that a timeout is treated as proof that the payer was right. It is a liveness safeguard. The system cannot leave someone else's USDC locked permanently because an external workflow did not complete.

## Why this matters for the payer

For the payer, cancellation appeals create a clear boundary around what cancellation means.

A payer can still stop a stream when circumstances change. They do not need permission from the payee to end future payments. But they also need to provide a reason and allow the payee to challenge the decision within the defined window.

The payer benefits from:

- Immediate payment of the payee's earned balance.
- Automatic protection of the unstreamed balance.
- A structured place to explain the cancellation.
- The ability to submit supporting evidence.
- A process where uncertainty does not automatically spend their escrow.
- A bounded timeline that prevents funds being locked indefinitely.
- A permanent onchain record of the cancellation and its outcome.

This makes cancellation more defensible. The payer does not have to rely on a private message or an informal promise that the dispute will be resolved later.

## Why this matters for the payee

For the payee, a cancellation does not erase money that has already been earned.

The accrued amount is paid at cancellation, and the remaining balance is held while the payee decides whether the cancellation should be challenged.

The payee benefits from:

- Immediate access to earned USDC.
- A 24-hour appeal window.
- The ability to submit agreements, work product, invoices, and communications.
- A shared Bant room for responding to the payer's explanation.
- Evidence reviewed against the exact cancellation reason.
- A path to resume the stream when the cancellation is shown to be illegitimate.
- A transparent record of the final decision.

This is especially important in ongoing work. A payee should not have to choose between accepting an unexplained cancellation and starting an expensive, disconnected dispute process. Cadence keeps the challenge close to the payment relationship.

## Why this improves the payer-payee relationship

The appeal process is not designed to make payer and payee adversaries. It is designed to make the relationship clearer when something goes wrong.

Most payment relationships work because both sides share an understanding of what is being delivered and when payment is earned. A cancellation becomes difficult when that understanding is no longer shared.

Cadence gives both parties a common process:

- The payer states why the stream was cancelled.
- The payee explains why the cancellation is disputed.
- Both sides submit evidence.
- The Bant room preserves the exchange.
- GenLayer reviews the committed record.
- Arc applies the final result.

That changes the relationship from "who can make the louder claim?" to "which version is supported by the record?"

It also keeps the financial consequences proportional. The payee does not lose accrued earnings, and the payer does not lose unstreamed funds simply because a dispute was opened.

The result is a payment relationship with room for disagreement without requiring either side to give up control of their money before the facts are clear.

## Under the hood

The appeal lifecycle is split between Arc and GenLayer.

Arc handles:

- Stream creation and escrow.
- Per-second accounting.
- Payment of accrued earnings.
- Cancellation requests.
- Appeal deadlines.
- Bant deadlines.
- Escrow release.
- Stream resumption.
- Final refunds.

GenLayer handles:

- Reading the committed evidence package.
- Reading the frozen Bant transcript.
- Comparing the evidence with the cancellation reason.
- Producing an upheld or rejected verdict.
- Returning the reason, confidence, summary, and findings.

The relay connects the two systems, but it cannot rewrite the case. It can only deliver the finalized verdict to the Arc contract.

Nothing about the appeal changes the basic promise of Cadence. Money still streams by the second. Earned money is still paid as it is earned. The appeal process exists for the moment when a payer stops the stream before all of the agreed balance has been streamed.

## Try it

Cadence is live on Arc testnet.

Open a stream, cancel it from the payer dashboard, and switch to the payee view to see the appeal window. Submit an evidence-backed appeal, open the Bant room, and follow the case as it moves from Arc to GenLayer and back again.

The appeal process is there so that "cancel" does not have to mean "the conversation is over."

https://www.cadenceonarc.tech/
