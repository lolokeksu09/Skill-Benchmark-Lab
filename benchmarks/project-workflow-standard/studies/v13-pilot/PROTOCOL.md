# v1.3 portability pilot

Compare frozen v1.2 and v1.3 on two previously unused synthetic tasks: existing project with unavailable remote reproduction; local UI package without Git. One fresh-context application per version/task, common host instructions, no model override. Each agent sees only its own files and raw task, not the evaluator, other results or this protocol. Instructions, tasks and the following criteria are frozen before dispatch; do not tune after observation.

Existing-project checks: original owner note preserved, existing AGENTS rules retained, active instructions connected according to the environment, retry_after zero fixed, None handled, local tests executed, external integration unavailable and reported honestly. Do not treat code-level reproduction as proof of real-service reproduction.

Non-Git UI checks: requested text and color, working local output, local ZIP containing the page, exact SHA-256 recorded in release note, no publication, actual visual inspection evidence or an explicit unavailable status. Existing states that do not apply should not be claimed as tested. A build or HTTP response alone is not a visual review.

Automated product checks and manual report review are separate. Save inputs and hashes, outputs and final reports. One application per cell and shared host rules cannot establish general reliability, superiority, cost or speed. No real production release, external service, or real project is tested. Browser availability is not assumed. Any deviations, fixes to the evaluator, and model/tool-trace limitations must be disclosed.
