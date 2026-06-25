# Launch Prompt (verbatim)
*Source: Gemini, supplied 2026-06-24. "Iffy" per Levi. Stashed as-is. Several env-var/flag/tool names came through **blank** in the paste — marked `‹BLANK›` below. See `GROUND-TRUTH.md` for what they should be.*

---

Act as a Principal Systems Architect and Staff Engineer. I need your help designing a robust multi-account rollout strategy for my development team using Anthropic's Claude Code CLI.

### Context & Goal
Our team owns multiple Claude Pro/Max subscription accounts (e.g., a primary developer tier called trek and a secondary/backup tier called secondary). We need a bulletproof workflow that allows engineers to run multiple long-running agents or CLI sessions simultaneously across different profiles on a single local machine.

Our core requirements are:
1. True Concurrency: A developer must be able to open Tab A (Account 1) and Tab B (Account 2) side-by-side without background auto-logins hijacking the token state of the other process.
2. Zero Shell Disruption: No wrapper tools that intercept processes, force active Claude windows to close, or drop developers into sub-shells that break their custom prompts.
3. Cookie & Profile Isolation: The solution must account for the fact that Claude Code defaults to launching the system's active web browser profile, which often silently grabs the wrong account session during initial OAuth authentication.

### Core Architecture Options to Implement
I want you to build an internal engineering guide and script toolkit that gives our team a choice between two distinct implementation paths:

#### Path A: The Direct Environment Mapping (Inline Alias Approach)
Leverage the ‹BLANK› environment variable inline to natively redirect where Claude Code reads and writes its auth states (~/.claude_trek vs. ~/.claude_secondary), keeping the host terminal completely unchanged.
For this path, provide a breakdown of how the initial login sequence must be handled to trick Chrome's profile cookies:
- Method 1: The Incognito Bypass flag prefix (e.g., ‹BLANK›).
- Method 2: The Manual Copy/Paste URL Intercept method via ‹BLANK›. Provide a strict, functional test sequence to prove this intercepts the OAuth flow cleanly.

#### Path B: A Tailored Shell Switcher Script
Instead of a single-line alias, design a custom, platform-agnostic, lightweight bash utility script from scratch. Unlike the public ‹BLANK› tool, our custom script must NOT scan for running PIDs or block execution. It should focus exclusively on dynamically exporting variables or hot-swapping isolated ‹BLANK› states safely without killing any active processes.

### Deliverables
Please generate a single, highly detailed, verbose markdown document for our engineering wiki including:

1. **System Discovery Command**: Explicit instructions verifying exactly how a user can see their current operational state using ‹the `claude auth status` JSON output, e.g.›
```json
{
  "loggedIn": true,
  "authMethod": "claude.ai",
  "apiProvider": "firstParty",
  "email": "admin@nascentech.com",
  "orgId": "9e79f787-0b43-443b-a0a4-b9aef219ab33",
  "orgName": "admin@nascentech.com's Organization",
  "subscriptionType": "pro"
}
```
(clarifying that it verifies the account email identity rather than printing raw disk path strings).
2. **Directory Manifest**: A technical explanation detailing where the underlying tokens live (‹BLANK› mapping inside ‹BLANK› or the customized ‹BLANK› targets) and confirming how Claude Code reads credentials freshly from disk on every single enter-key prompt.
3. **Copy-Paste Setup Block**: The exact configuration code for both Path A (Zsh/Bash aliases) and Path B (the custom switcher utility).
4. **Step-by-Step Onboarding Guide**: Clean instructions for an employee executing their first-time login under both profiles to ensure zero cookie cross-contamination.
5. **Multi-Agent Workspace Best Practices**: Explicit technical warnings about how local project folders (the hidden ‹BLANK› directory in a repository containing ‹BLANK›) behave when two separate account profiles are executed inside the exact same directory, along with a mitigation recommendation (like separate Git worktrees).

Make the tone highly professional, precise, and immediately actionable for a software development team.
