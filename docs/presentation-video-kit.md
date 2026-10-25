# DealDesk Local: HTML presentation and video kit

Prepared for the five-person team: Michael, Luis, Khushi, Suhas, and Jai.

## Use and scope

The central story is: a salesperson needs a defensible quote, and changing costs can make that quote unsafe before the customer signs. DealDesk Local prepares the recommendation from private evidence and keeps checking the assumptions.

The project brief records an under-two-minute Round 1 submission video and a three-minute finalist demo. This kit provides the requested three-minute master plus a 1:55 cut. The signed-in organizer dashboard could not be rechecked during preparation; the timing distinction comes from the repository's day-of event notes.

The inspected README describes a planning repository, rather than an implemented application. The narration below is intended for the finished demonstration. Record only functioning features as product evidence. Label unfinished interfaces as prototypes and replace completed-action claims with design intent when necessary. All numerical examples and policies here are synthetic.

## Copy-paste prompt for the HTML presentation

```text
Create a complete, polished HTML presentation for DealDesk Local, designed to support a three-minute Dell × NVIDIA hackathon video.

Deliver one self-contained presentation.html with inline CSS and JavaScript. Return the complete code. This is a browser slide presentation, not a scrolling website. Do not build the underlying product.

Audience and objective
The audience is hackathon judges and sales leaders. By the end, they should understand the sales problem, the workflow, why local inference matters, and why the scheduled cost review makes this useful beyond a one-time chat response. Favor product evidence over long explanations of AI.

Product facts
DealDesk Local is designed for enterprise account executives and sales managers. It combines authorized internal account research, company pricing policy, and dated delivery/service costs to prepare a defensible offer. A local model handles language and evidence synthesis. Deterministic code calculates money, checks margin/discount rules, and enforces release conditions. A person reviews and releases the quote. A scheduled watcher flags open quotes when cost assumptions change.

The intended deployment uses the supplied Dell Pro Max with GB10, local inference, and OpenClaw for orchestration and scheduled work. Show only the actual runtime/model that the team has verified. Do not add unimplemented stack components or claim vendor endorsement.

Slack or Telegram is the salesperson's request and notification channel. The demonstration should use whichever channel is actually integrated. Do not imply both are working without recordings of both. Requests use opaque deal references. Notifications use a fixed message such as “A quote review is ready. Open your local DealDesk viewer.” Confidential documents, customer names, prices, costs, and margins belong in the authenticated local viewer. Messaging uses external transport. Say “Inference and sensitive pricing evidence stay on company hardware,” rather than claiming the whole system never uses the internet.

Story and factual example
Use one synthetic quote, Q-104, throughout. Q-104 is an illustrative identifier, not a claim about an existing record.
- List contract price: $160,000.
- Standard offer: $144,000, a 10% discount.
- Negotiated offer: $136,000, a 15% discount requiring director approval.
- Initial stress cost: $97,600.
- Stress gross margin at $136,000: 28.24%.
- Synthetic minimum stress gross margin: 25%.
- Updated stress cost: $105,600.
- Same $136,000 quote after the update: 22.35% stress gross margin.
- Revised economic floor: $140,800.
Label the figures “Synthetic demonstration” and identify the margin basis as the stress scenario. The floor is a policy constraint, not proof that a customer will pay that price. Preserve the original quote and approval history. The update creates a review hold/new appraisal. Revised terms require a fresh version and approval. Do not silently reprice or send a customer offer.

Create exactly seven main slides, with this 180-second recording plan

1. 0:00–0:08, Michael: DealDesk Local
   Minimal cover. Subtitle: “Private pricing intelligence for sales teams.”
   Main hook: “A quote can win the deal and still lose margin.”
   Small footer: “Dell × NVIDIA hackathon prototype.”
   Use a clean typographic composition. An optional background video must not compete with the title.

2. 0:08–0:25, Michael: The sales quoting problem
   Show a simple sequence of fragmented inputs: customer research, company policy, delivery costs, then the salesperson's quote.
   Main takeaway: “The quote is only as safe as its assumptions.”
   Brief supporting copy explains that the rep must assemble confidential evidence while costs and negotiations change. Do not add invented productivity statistics or market size.

3. 0:25–1:05, Luis: A sales request and its evidence
   Prioritize a large, replaceable real screen recording. Show the implemented messaging channel, then the local offer and one clickable source passage.
   Minimal labels: “Request,” “Local evidence,” and “Offer.”
   Show the $144,000 standard offer in the real product footage.
   Make the recording occupy at least 75% of the slide. Keep surrounding copy below 25 words. If no recording is provided, show a clearly labeled “Replace with actual product recording” placeholder. Do not fabricate a working chat interface.

4. 1:05–1:40, Khushi: A concession with clear approval rules
   Show the $136,000 concession, 15% discount, 28.24% stress gross margin, and “Director approval required.”
   Prefer the real negotiation and approval interface recording. A simple editable numerical comparison may supplement it.
   Include the short line “Code calculates the money. People approve the offer.”
   Do not display sensitive numerical details inside Slack or Telegram.

5. 1:40–2:25, Suhas: The cost update that changes the decision
   Show the real cost-feed update, scheduled review event, generic messaging notification, and resulting local risk view.
   Make the central numerical change easy to read: “28.24% to 22.35% projected margin.” Label it as the stress scenario.
   Show “25% policy floor,” “Review required,” and “Revised economic floor $140,800.”
   Keep the offer itself at $136,000 so viewers understand the changed assumption. Preserve the earlier quote/approval record. Do not animate the offer automatically changing to $140,800.
   If the demo uses a shortened schedule or accelerated waiting time, show a small factual label. A manual trigger must be labeled as manual.

6. 2:25–2:50, Jai: Local execution and hackathon relevance
   Use a simple editable architecture diagram with an explicit GB10 boundary. Keep messaging outside it. Put the local model, document retrieval, pricing/policy tools, stored quote versions, and watcher inside it.
   Add a real proof image or short recording of the selected local inference route. A GPU chart alone is insufficient to establish that inference is local. If available, show a fresh local quote while disconnected, with the notification queued for reconnection.
   Tie the demo to the four judging categories recorded in our event notes: technical execution, business value, local-first design, and demo quality. Keep weights and detailed evidence in speaker notes unless reconfirmed against the current organizer dashboard.
   Use OpenClaw as the planned runtime label only if the actual demo uses it. Include an editable placeholder for the verified local model name.

7. 2:50–3:00, Jai: Value for the sales team
   Closing line: “A defensible offer, with an early warning when its assumptions change.”
   Identify the daily user as the account executive and the buyer as Sales or Revenue Operations leadership.
   Small team credits: Michael, Luis, Khushi, Suhas, Jai.
   Include editable repository/demo link fields. Hide empty fields in recording mode. Do not invent customers, ROI, accuracy, latency, revenue saved, or test results.

Visual direction
Use a restrained enterprise look: deep charcoal background, warm white text, one green accent, and amber for review conditions. Treat green as a design choice, not an implied official NVIDIA theme. Use red sparingly. Favor one strong composition per slide. Avoid dashboard-style card grids around the actual product recording. Use original screenshots or empty media placeholders rather than generic AI brain imagery, robot mascots, fake terminals, or invented hardware diagrams.

Use a 1920×1080 design canvas with a 16:9 aspect ratio. Scale proportionally and letterbox on other viewport sizes. Keep generous margins and a clear caption-safe area. At the design canvas size, use approximately 72–88px titles and 32–40px body copy. Cut text before reducing sizes. Monetary amounts should remain legible in a 1080p video. Use system fonts and no external CDN dependencies.

Interaction and recording
- Show one slide at a time, with no page scrolling.
- Left/right arrow keys navigate. F toggles fullscreen. N toggles speaker notes. A toggles autoplay. R resets the presentation and timer.
- Keep manual navigation as the default. Autoplay uses slide durations of 8, 17, 40, 35, 45, 25, and 10 seconds.
- Add an elapsed timer, slide number, and subtle progress indicator in the presenter controls, outside the recorded composition when possible.
- Add ?record=1 to hide controls, notes, and unused placeholders that are not meant for the video. Missing required demo media should still have an explicit placeholder, never a fake recording.
- Use short 150–250ms fades and honor prefers-reduced-motion. Avoid continuous decorative motion.
- Video elements need controls in edit mode, muted inline playback, and a clean fallback. Use relative media paths in an editable configuration object. Do not embed large video files as base64.
- Include print CSS with one slide per page.

Speaker notes
Include editable notes for each slide with speaker name, duration, what to record, and the matching script. Keep all notes out of the main frame and recording mode.

Truthfulness and completion
The source repository currently contains the plan and pricing reference data, not the integrated application. Design the deck for real recordings supplied by the team. Label any unfinished feature as planned or prototype. Never use an animation or Veo-generated shot as evidence that an integration, inference route, approval, or scheduled watcher works.

Return the full HTML and a short usage guide covering opening it locally, replacing media paths, navigating, and recording. Check the seven-slide count, 180-second duration sum, text overflow, offline operation of the deck itself, keyboard controls, reduced motion, and numeric consistency.
```

## Three-minute script and shot plan

Use a short on-camera introduction if desired, then let each person narrate the product footage. One voice handoff per person keeps the recording easy to edit. The script leaves time for clicks and brief pauses.

| Time | Speaker | Picture |
|---|---|---|
| 0:00–0:25 | Michael | Cover, then fragmented quoting inputs |
| 0:25–1:05 | Luis | Real channel request, local offer, source passage, customer draft |
| 1:05–1:40 | Khushi | Concession, margin, director approval state |
| 1:40–2:25 | Suhas | Cost update, scheduled review, notification, local risk view |
| 2:25–3:00 | Jai | Local execution proof, hackathon fit, business close |

### Michael

“Sales teams need to quote quickly. But customer research, pricing rules, and delivery costs sit in different files. A rep can win a deal and still lose margin, especially when costs change before the customer signs. DealDesk Local brings that private evidence together and keeps checking whether the quote still makes sense.”

### Luis

“Here is the salesperson's workflow. I request a quote through our connected messaging channel using a deal reference, then open DealDesk locally. The standard offer is one hundred forty-four thousand dollars. I can open the source passages behind it and review the customer's requirements. The internal view shows the economics. A separate customer draft explains the offer without exposing our costs or margins.”

### Khushi

“Now the customer asks for one hundred thirty-six thousand dollars. That is a fifteen-percent discount from list. Our pricing code calculates a twenty-eight-point-two-four-percent margin under the cost-stress scenario. It meets our twenty-five-percent floor, but the discount still requires director approval. The model explains the recommendation. Code calculates the money and checks the rules.”

### Suhas

“Now a supplier-cost update arrives. The scheduled watcher checks the open quote. With the new costs, the same offer has a projected margin of twenty-two-point-three-five percent, below our policy floor. The agent flags it for review and sends a simple notification. Back in DealDesk, the salesperson sees what changed and the revised minimum price. The original quote stays in history. A person must review any new terms.”

### Jai

“We run inference and sensitive pricing tools locally on the Dell GB10, with OpenClaw coordinating the workflow. That connects the hackathon's local AI requirement to a practical business task and an agent that keeps working after the first request. For sales teams, the value is a defensible offer and an early warning when its assumptions change. That is DealDesk Local.”

Use Suhas's scheduled-watcher wording and Jai's runtime wording only after recording those working components. If unfinished, say “Our design uses…” and label the feature as planned. Name Slack or Telegram in Luis's first line when that is the working channel.

## Exact screen-recording sequence

1. Prepare one synthetic deal and a clean session. Increase interface text size so the offer, sources, and approval state are readable.
2. In the working Slack or Telegram integration, send the opaque deal reference using the actual supported syntax. “Prepare Q-104” is an illustrative interaction, not an implemented command specification.
3. Open the authenticated local viewer. Show the $144,000 standard offer, then one source passage. Briefly show the separate customer draft.
4. Request the $136,000 concession. Pause on the 15% discount, 28.24% stress margin, and director approval requirement. If approval is implemented, record the authorized director approving that exact version.
5. Introduce the synthetic cost-feed update. Capture the scheduled watcher processing it and creating a review event. A short genuine demo interval is acceptable if labeled. Do not present a manual invocation as unattended execution.
6. Show the generic notification in the same messaging channel. Return to the local viewer and pause on 22.35%, the 25% floor, $140,800 revised economic floor, and the review hold.
7. Show that the original quote and any approval remain in history. Explain that revised terms need fresh review and approval.
8. Capture the selected local model route and, if available, a fresh local request while disconnected. Offline inference does not imply offline messaging; queue its notification until connectivity returns.

Do not spend scarce video time repeating the full workflow in a second messaging platform. If both integrations work, a two-second inset showing the same generic notification is enough. Otherwise describe the second channel as an extension of the design.

## Gemini Veo prompts for optional supporting clips

Use real screen recordings for product functions. Use at most two brief Veo inserts, totaling roughly 6–10 seconds, inside the existing timeline. Generate each shot separately. Add exact titles, numerical overlays, and the “AI-generated illustration” label in the editor. The prompts deliberately specify subject, action, camera, lighting, and audio, following Google's official Veo prompting guide: https://deepmind.google/models/veo/prompt-guide/.

### Clip A: The fragmented sales workflow

Place a four-second excerpt under Michael's problem statement.

```text
Create an eight-second, 16:9 live-action-style B-roll shot for an enterprise sales software presentation. A sales representative in their early thirties sits at a modest modern office desk with a laptop, a printed quotation, and a small stack of supplier paperwork. In one continuous action, they compare the quotation with a new supplier cost sheet, pause thoughtfully, and turn back to the laptop. Medium over-the-shoulder framing, slow subtle camera push-in, natural late-afternoon window light, charcoal and muted blue palette. Keep all document text and screen content softly out of focus. Leave the left third visually quiet for a title added later. Emotion: focused concern, not panic. Audio: quiet office ambience and one paper movement. No dialogue, music, generated captions, logos, readable prices, futuristic holograms, or exaggerated acting. This is an illustrative office scene, not a product demonstration.
```

### Clip B: Local processing on company hardware

Optional three-second bridge into Jai's explanation. Prefer actual footage of the supplied GB10 when available.

```text
Create an eight-second, 16:9 conceptual product B-roll shot showing local computing at a business workspace. A compact, unbranded desktop workstation sits beside a monitor in a real small office. Start with a close view of the workstation and slowly slide the camera sideways to include a professional reviewing an intentionally unreadable interface on the monitor. Restrained documentary realism, soft daylight, matte charcoal equipment, warm neutral surfaces, one subtle green desk accent. Keep the workstation design physically plausible and generic. Leave clear negative space in the upper left for an editor-added caption. Audio: soft fan noise and quiet room tone. No dialogue, music, logos, hardware specifications, visible network diagrams, floating files, cloud graphics, or readable screen text. This clip illustrates on-premises computing and must not imply it documents the actual Dell hardware or proves data privacy.
```

### Clip C: A useful review alert

Optional three-second insert within Suhas's segment. Overlay a real notification recording in the editor if it improves clarity.

```text
Create an eight-second, 16:9 realistic office insert. An account executive works at a laptop with an unbranded smartphone lying face-up nearby. The phone gives one subtle vibration and its screen softly lights up with an unreadable notification. The person notices it and turns their attention back to the laptop to review the issue. One continuous close shot at desk height with a gentle focus shift from phone to laptop. Match a restrained enterprise visual style with natural daylight, charcoal surfaces, and soft neutral colors. Keep every interface and notification out of focus so real screen footage can be composited later. Leave space above the phone for an editor-added caption. Audio: one soft notification tone and quiet room ambience. No dialogue, music, logos, generated UI text, flashing red alerts, or dramatic acting. This is an illustrative notification moment, not evidence of a functioning Slack or Telegram integration.
```

For the margin change, use the real product screen or editable HTML text animation. Keep exact financial values out of generated video.

## Under-two-minute cut: 1:55

Use this version if the submission follows the under-two-minute requirement recorded in the project brief. Remove the optional Veo footage and retain all five speakers with these short lines.

| Time | Speaker | Short script |
|---|---|---|
| 0:00–0:15 | Michael | “A sales quote depends on private customer research, pricing policy, and delivery costs. Those costs can change before the customer signs. DealDesk Local prepares a defensible offer and keeps watching its assumptions.” |
| 0:15–0:40 | Luis | “The rep starts in our connected messaging channel, then opens the private local viewer. Here is the offer and a source passage supporting it. Internal costs stay in this view. The customer gets a separate explanation.” |
| 0:40–1:00 | Khushi | “This one-hundred-thirty-six-thousand-dollar offer meets our initial margin rule, but its fifteen-percent discount needs director approval. Code calculates the money and checks those rules.” |
| 1:00–1:30 | Suhas | “A new supplier-cost update changes the decision. The scheduled watcher finds that this same offer now falls below our twenty-five-percent margin floor. It sends a review notification. DealDesk shows the changed assumptions and preserves the original quote.” |
| 1:30–1:55 | Jai | “Inference and sensitive pricing tools run locally on the supplied Dell GB10. OpenClaw coordinates the work and scheduled review. A person approves revised terms. We connect local AI to a useful sales workflow that keeps working after the first request.” |

The same implementation qualifications apply to this shorter script. Leave five seconds below the two-minute limit and use the organizer's latest dashboard instructions for the actual submission.
