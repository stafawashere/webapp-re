# OpenAPI 3.1 output

The finding files stay the source of truth. The spec is rendered from them so code generators,
docs and diff tools can consume the contract. Load the **web-api-reverse-engineering** skill for
its discovery-notes vocabulary and spec skeleton, and apply the mapping below.

## Mapping

| Finding | OpenAPI |
|---|---|
| `method` + `url` path | `paths.<path>.<method>`, ids as `{name}` path parameters |
| `url` origin | `servers[]`, one entry per origin |
| `operation` or `id` | `operationId`, camelCase of the finding id |
| `goal` | `summary` |
| query parameters, form fields, JSON body | `parameters[]` and `requestBody` with schemas from observed shapes |
| response shape | `responses.200.content.<type>.schema` built from `shape.py` output; a field with partial coverage is not `required` |
| failure signals | `responses.200` `oneOf` the success schema and the error envelope, plus documented 4xx entries actually observed |
| required cookies | `components.securitySchemes.<name>: { type: apiKey, in: cookie, name: <cookie> }` |
| required headers | `parameters` with `in: header` and `x-value-source` naming where the value comes from |
| status, counts, dates | `x-provenance: { finding, status, verify_count, last_verified, runs }` |
| ablation result | `x-required` and `x-ignored` lists |
| persisted query or doc id | `x-operation-id-rotates: true` and the id in `x-operation-id` |

GraphQL endpoints that multiplex many operations on one path: emit one path per operation using a
`#operation` suffix in an `x-graphql-operation` extension and a discriminating `requestBody`
example, or emit a separate path key per operation with a fragment such as `/api/graphql#ProfileQuery`.
Pick one per spec and say which in `info.description`.

Only `verified` findings go into `paths`. Hypotheses are listed in `x-hypotheses` so the spec never
claims an unreplayed contract works.

## Checks

- The file parses as YAML and declares `openapi: 3.1.0`.
- If `npx` is available and the user agrees to the download, `npx @redocly/cli lint` validates it;
  otherwise parse it with Python and check every `$ref` resolves.
- No example carries a cookie value, token or personal content.
