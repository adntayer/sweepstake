---
name: to-issues
description: Break a plan, spec, or PRD into independently-grabbable issues on the project issue tracker using tracer-bullet vertical slices. Use when user wants to convert a plan into issues, create implementation tickets, or break down work into issues.
---

# To Issues

Break a plan into independently-grabbable issues using vertical slices (tracer bullets).

The issue tracker and triage label vocabulary should have been provided to you — run `/setup-matt-pocock-skills` if not.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes an issue reference (issue number, URL, or path) as an argument, fetch it from the issue tracker and read its full body and comments.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. Issue titles and descriptions should use the project's domain glossary vocabulary, and respect ADRs in the area you're touching.

### 3. Draft vertical slices

Break the plan into **tracer bullet** issues. Each issue is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

Slices may be 'HITL' or 'AFK'. HITL slices require human interaction, such as an architectural decision or a design review. AFK slices can be implemented and merged without human interaction. Prefer AFK over HITL where possible.

<vertical-slice-rules>
- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
</vertical-slice-rules>

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: short descriptive name
- **Type**: HITL / AFK
- **Blocked by**: which other slices (if any) must complete first
- **User stories covered**: which user stories this addresses (if the source material has them)

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are the correct slices marked as HITL and AFK?

Iterate until the user approves the breakdown.


### 5. Create Markdown Files

For each approved slice, create a separate `.md` file instead of publishing to the issue tracker.

Generate the files in dependency order (blockers first) so that dependency references can point to actual file names.

Store all generated files in the designated output directory unless otherwise specified by the user.

Use the following template for each file:

# `<plan-filename>_<NNNN>_<slice-title>.md`

## Parent

A reference to the parent issue, PRD, specification, or plan (if applicable). Otherwise omit this section.

## What to Build

A concise description of this vertical slice. Describe the end-to-end behavior rather than layer-by-layer implementation.

Avoid specific file paths or code snippets, as they become stale quickly. Exception: if a prototype produced a decision-rich artifact (such as a state machine, reducer, schema, or type definition) that communicates an important design decision more clearly than prose, include only the relevant portion and note that it originated from a prototype.

## Acceptance Criteria

* [ ] Criterion 1
* [ ] Criterion 2
* [ ] Criterion 3

## Blocked By

* `<blocking-slice-file>.md`

Or:

`None - can start immediately`

### Output Requirements

* Create one Markdown file per approved vertical slice.
* Use kebab-case file names (for example: `user-can-create-project.md`).
* Generate files in dependency order.
* Ensure every slice remains independently understandable and executable.
* Preserve all dependency relationships.
* Do not modify the source plan, PRD, specification, or parent issue.
* The generated Markdown files should be ready to commit directly into the repository.

These Markdown files are considered implementation-ready work items for AFK agents unless otherwise specified.
