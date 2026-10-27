# MANDATORY PLAN FIDELITY & ZERO-COMPROMISE EXECUTION RULE

> [!CAUTION]
> ## 🚨 P0 INVARIANT: ZERO-COMPROMISE PLAN FIDELITY 🚨
> Whenever preparing a plan (`/plan`), reviewing an audit, or executing plan tasks:
> 1. **MANDATORY SKILL ACTIVATION**: The AI assistant MUST activate and adhere strictly to the **`plan-fidelity-auditor`** skill (`~/.gemini/config/skills/plan-fidelity-auditor/SKILL.md`).
> 2. **NO SCOPE DILUTION / COMPROMISE**:
>    - If an audit or plan states `[COMBINE]`, the agent is **STRICTLY PROHIBITED** from substituting a cosmetic rename (e.g. adding numbers `1.` and `2.` to separate tabs). `[COMBINE]` strictly means merging the elements into the same parent container (`<page>`, `<group>`, etc.).
>    - If an audit states `[ELIMINATE]`, the element must be completely removed or hidden with `invisible="1"`.
> 3. **MANDATORY VISUAL WIREFRAME**: Every plan modifying UI forms, tabs, or menus must provide an explicit ASCII wireframe mockup showing the human user experience before and after the change.
> 4. **PROGRAMMATIC ARCHITECTURAL ASSERTIONS**: Before declaring an execution complete, the assistant must run an active XPath/AST assertion script verifying:
>    - Exact element counts.
>    - Parent-child container relationships (e.g., asserting that merged lines share the same parent `<page>`).
>    - The total absence of eliminated ghost elements.
