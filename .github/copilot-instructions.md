# Project Guidelines

## Pull Request Review

- During pull request review, check whether the current file changes alter the API contract that the Camel integration layer depends on.
- Focus this review on contract-impacting changes, not on unrelated refactors.
- Treat this as advisory only: warn when impact is likely or plausible, but do not treat it as a blocking requirement by itself.

## API And Integration Contract Checks

- Pay extra attention when changes touch API response shaping or filtering code such as `meldingen/api/v1/endpoints/melding.py`, `meldingen/schemas/output.py`, `meldingen/schemas/output_factories.py`, `meldingen/models.py`, `meldingen/dependencies.py`, or authentication-related flows.
- Warn if the current changes modify field names, field nesting, field types, pagination shape, `_links`, `results`, `count`, state names, state filtering semantics, authentication expectations, or required headers used by the integration layer.
- When warning, mention the likely integration files to verify inside these folders:
  - `integrations/routes/*`
  - `integrations/tools/*`
- If the changed files are unlikely to affect the integration layer, say that briefly instead of raising a generic warning.

## Review Style

- Keep integration-impact comments concrete and file-specific.
- Prefer comments like "This change may require an update in the V1 DataSonnet transform" over generic statements like "Check integrations".
- If the impact is uncertain, say what should be verified rather than assuming it is broken.