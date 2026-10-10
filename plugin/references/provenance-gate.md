# Provenance gate

A client built on an undocumented API fails silently when someone writes an endpoint from memory:
the site answers 200 with an error envelope, or a null, and nothing downstream notices. A
provenance gate makes "every endpoint literal in the client was observed and replayed" a
mechanical check instead of a habit.

## Shape of the gate

A script in the consumer project, run with its other checks, that:

1. Loads every finding with `status: verified` and `verify_count >= 2`, and builds the set of
   backed URL shapes (host plus path with ids replaced by placeholders), operation ids, and hosts.
2. Scans the client's source for URL literals, path literals, host literals, operation ids and
   failure-code literals compared against error fields.
3. Fails, naming file and line, when a literal has no backing finding.
4. Accepts a per-line escape such as `# provenance: ignore, <reason of ten characters or more>`
   for literals that are genuinely not endpoints, and reports an escape with no reason.
5. Runs positive controls first: a fixture with known unbacked literals must produce exactly the
   expected count, or the gate reports itself unrunnable. A zero from a dead scanner is the
   failure the controls exist to catch.

## When it fires

At the moment a session must write a URL, a path, an operation id, a required header, a gating
cookie, or a failure field into client code, it checks the site's `knowledge/INDEX.md`:

| Index state | Action |
|---|---|
| verified within 30 days | build from it, cite the finding id in the change |
| older, stale, or hypothesis | replay first |
| nothing | run discovery for that goal first |

The generated programs from `/webapp-re:engineer` carry a gate of this shape. A
mature gate also checks that each persisted-query call carries the same operation id, name and
path as the finding it cites, and lists stop-only markers (literals the client only uses to
recognise a challenge and never sends) as named exemptions, one file each.

Adding an exemption is loosening a gate, which is the user's decision.
