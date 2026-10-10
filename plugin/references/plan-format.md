# plan.json format

```json
{
   "site": "example",
   "skill_name": "example",
   "generated": "2026-10-09",
   "scope_generated": "2026-10-08",
   "program": {
      "language": "python",
      "package": "example_client",
      "cli": "example",
      "session": "cookies adopted from the user's browser, read from <root>/.env",
      "pacing": "one request in flight, 3 s minimum gap with jitter"
   },
   "sub_skills": [],
   "commands": [
      {
         "name": "help",
         "purpose": "List every command, its inputs, outputs and readiness",
         "kind": "read",
         "input_schema": { "type": "object", "properties": {} },
         "output_schema": { "type": "object", "properties": { "commands": { "type": "array" } } },
         "depends_on": [],
         "requests": 0,
         "failure_classes": [],
         "open_steps": []
      },
      {
         "name": "fetch-saved-items",
         "purpose": "Return the items on the user's saved list",
         "kind": "read",
         "input_schema": { "type": "object", "properties": { "limit": { "type": "integer" } } },
         "output_schema": {
            "type": "object",
            "required": ["items"],
            "properties": {
               "items": {
                  "type": "array",
                  "items": {
                     "type": "object",
                     "required": ["id", "name"],
                     "properties": {
                        "id": { "type": "string" },
                        "name": { "type": "string" },
                        "price": { "type": ["string", "null"] },
                        "saved_at": { "type": ["string", "null"] },
                        "status": { "type": ["string", "null"] }
                     }
                  }
               }
            }
         },
         "depends_on": [ { "endpoint": "saved-items", "finding": "list-saved-items", "state": "hypothesis" } ],
         "pagination": "none",
         "requests": 1,
         "failure_classes": ["SessionExpired", "ChallengeRequired", "RateLimited", "ApiError", "ContractBroken"],
         "confirmation": null,
         "open_steps": [ { "step": "replay list-saved-items twice", "budget": 2 } ]
      }
   ],
   "build_order": [
      { "step": 1, "do": "session adoption, transport, pacer, classifier", "commands": ["help"], "exit_check": "help prints session status" },
      { "step": 2, "do": "first authenticated read", "commands": ["fetch-saved-items"], "exit_check": "live run returns at least one item" }
   ],
   "risks": ["price field absent on some items in the scope sample"]
}
```

Rules the checker enforces:

- `commands[].name` unique, kebab case, and `help` present.
- Every command has `input_schema` and `output_schema` objects.
- Every `depends_on[].endpoint` exists in `scope.json` endpoints.
- Every command appears in exactly one `build_order` step.
- `kind` is `read` or `write`, and every `write` has a non-null `confirmation`.
