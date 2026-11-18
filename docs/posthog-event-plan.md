# PostHog event plan for the vocal separation tutorial

This plan describes how to measure engagement with [How to make a vocal separation engine for music](https://mkovalic.github.io/stemsplit/) and successful use of its tutorial. These are proposed event names; analytics have not been implemented, and the names do not represent confirmed events in Modal's existing analytics.

The article can observe browsing and clicks. Execution events require instrumentation in Modal, its CLI, or the tutorial script.

## Events on the article

1. **`$pageview` — when the article opens.**

   Record the article version and referral source. This tells us how many people arrive and which channels bring them.

2. **`docs_section_viewed` — when a section becomes visible.**

   Record `section_id`, such as `build-the-environment`, `run-multiple-songs-in-parallel`, or `estimate-cost-and-performance-at-scale`. This shows which parts people reach, not whether they understand or complete them. Count each section exposure once per page visit.

3. **`docs_code_copied` — after a code block is successfully copied.**

   Record which block: install command, image definition, separation function, single-song command, or batch command. This shows which instructions generate implementation intent and where people begin.

4. **`docs_markdown_copied` — after “Copy page” successfully copies the article.**

   This shows demand for the portable, agent-friendly version. It does not tell us whether an AI agent actually used it.

5. **`docs_markdown_download_clicked` — from either Markdown download control.**

   This shows intent to save the tutorial for use elsewhere. Record the control's location; a click does not confirm that the file was saved.

6. **`docs_github_clicked` — on “View on GitHub.”**

   This shows interest in the complete working project. We cannot infer a clone or successful run from this event.

7. **`docs_cta_clicked` — on the Modal account link and supporting documentation links.**

   Use a `destination_type` property such as `create_account`, `gpu_requirements`, or `billing`. This helps distinguish onboarding interest from questions about requirements and costs. Clicking the account link is not a completed signup.

Together, these events tell us whether readers find the article, reach relevant sections, and take steps toward trying it. Attach a stable `doc_id` and `doc_version` to each event so we can compare revisions of the article.

## Events while following the tutorial

These milestones would be observable only if the relevant systems were instrumented. Existing Modal users may skip account creation and CLI setup, so these are not mandatory steps in a single funnel.

1. **`signup_completed` — a new Modal account is created.**

   This shows conversion into a registered developer. Existing users skip this step. It requires Modal-side tracking.

2. **`cli_auth_succeeded` — `python -m modal setup` successfully authenticates the CLI.**

   This shows that the developer has connected their local environment to Modal. It does not prove their script works yet.

3. **`image_build_completed` — the environment build finishes.**

   Include `status`, duration, and whether cached layers were used. This shows whether dependency setup is succeeding and would capture problems such as a missing NumPy dependency. It requires build-system instrumentation.

4. **`workload_submitted` and `workload_started` — the song is accepted, then execution begins.**

   These are two events linked by a `run_id`. The gap measures the wait before execution, including queueing and startup. It helps explain a pending run and distinguish infrastructure waiting from confusing instructions.

5. **`example_run_succeeded` — Demucs finishes and produces the expected two outputs.**

   This is the first strong activation signal: the developer has successfully used cloud compute to separate a song. It does not establish that the stems sound good or were saved locally.

6. **`stems_saved` — both WAV files are successfully written locally.**

   This confirms that the tutorial delivered its promised result to the developer's computer. It needs explicit local-script instrumentation; the website and remote function cannot confirm it.

7. **`workload_failed` — an attempt fails.**

   Record a safe failure category and stage, such as dependency build, input validation, GPU execution, or output saving. This shows which failures a documentation improvement might prevent. The reporting source depends on the stage: local validation and saving failures require CLI or script instrumentation, while cloud failures can be reported by the platform.

8. **`batch_run_completed` — the parallel-song walkthrough finishes.**

   Record songs attempted, succeeded, and failed, linked by a `batch_id`. This shows progression from the single-song example to using the scaling instructions.

9. **Another successful run on a later day — measured from the same success events.**

   No special adoption event is needed. A later independent run suggests continued use beyond the initial tutorial. Multiple songs in one batch count as one batch journey, not multiple activated developers.

Useful properties include `run_id`, `batch_id`, `workspace_id`, and `example_id` where available. Song filenames, audio contents, source code, credentials, and raw logs are unnecessary for this measurement.

The strongest tutorial success measure is readers who reach `stems_saved`, followed by those who return for another run. Where local telemetry is unavailable, `example_run_succeeded` is a narrower, observable success measure. Connecting either outcome to an article visit requires an explicit identity and attribution connection; adding PostHog to the GitHub Pages site alone would not provide it.
