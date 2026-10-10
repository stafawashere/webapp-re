export const meta = {
   name: "webapp-re-optimize-apply",
   description: "Apply accepted optimize findings to one site's skills and program, one agent per file partition, then a rules review",
   whenToUse: "Phase 2 of /webapp-re:optimize. Pass the args object described in skills/optimize/SKILL.md",
   phases: [
      { title: "Fix", detail: "chain partitions one at a time, parallel partitions alongside" },
      { title: "Review", detail: "one reviewer checks every change against the pipeline rules" },
   ],
}

const FIX_SCHEMA = {
   type: "object",
   properties: {
      results: {
         type: "array",
         items: {
            type: "object",
            properties: {
               id: { type: "string" },
               outcome: { type: "string", enum: ["fixed", "skipped", "no-change-needed"] },
               reason: { type: "string" },
               files_changed: { type: "array", items: { type: "string" } },
               tests_added: { type: "array", items: { type: "string" } },
               bite_proof: { type: "string" },
               live_check: { type: "string" },
            },
            required: ["id", "outcome", "reason", "files_changed", "tests_added", "bite_proof", "live_check"],
         },
      },
      needs_files: { type: "array", items: { type: "string" } },
   },
   required: ["results", "needs_files"],
}

const REVIEW_SCHEMA = {
   type: "object",
   properties: {
      violations: {
         type: "array",
         items: {
            type: "object",
            properties: {
               file: { type: "string" },
               line: { type: ["integer", "null"] },
               rule: { type: "string" },
               detail: { type: "string" },
            },
            required: ["file", "line", "rule", "detail"],
         },
      },
      notes: { type: "string" },
   },
   required: ["violations", "notes"],
}

const RULES = [
   "Rules that hold for every change:",
   "- Edit only the files listed for your partition. If a fix needs another file, do not touch it; mark the finding skipped and list the file in needs_files.",
   "- Session adoption only. Never add a password login, never store a password, never accept cookies or tokens on argv.",
   "- Every endpoint literal in the program is backed by a knowledge base finding with status verified and verify_count 2 or more. Do not add a literal without one; if a fix needs a new endpoint, skip it with that reason.",
   "- No requests to the site at all. Do not run the program's CLI against the site, its live check script, or anything that sends a request. A fix whose proof needs a live read or write is implemented and tested offline, and its exact live check goes in live_check for the main session, which asks the user before any write.",
   "- Never loosen a test, gate, threshold, tolerance or fixture to make something pass. Strengthening is allowed.",
   "- Before writing or changing a test, name in one sentence the defect it catches. After writing it, break the fix, run that one test and watch it fail, then restore the fix and watch it pass. Put both outcomes, with the quoted pytest summary lines, in bite_proof.",
   "- Pacing defaults are never lowered as a speed fix.",
   "- Keep command names and their inputs stable; users already type them.",
   "- Style: match the file's indentation (3 spaces in this pipeline's code), double quotes, descriptive names, compound conditions split into named variables, blank lines between logical blocks, comments only where a person would write one, no em dashes, no emojis, no trailing blank line at the end of a file. Python through uv only.",
   "- Never print a cookie, token or other secret value.",
].join("\n")

function fixPrompt(context, partition) {
   const findings = partition.findings.map(finding => JSON.stringify(finding)).join("\n")

   return [
      "You are applying verified audit findings to the automation program and skills for the site " + context.site + ".",
      "",
      "Site root: " + context.root,
      "Program: " + context.program_dir + " (offline test command: " + context.test_command + ")",
      "Pipeline references: " + context.skill_root + "/references/",
      "Your partition " + partition.id + " may edit only these files:",
      partition.files.join("\n"),
      "",
      RULES,
      "",
      "Before acting on each finding, re-read the file at the line and confirm the defect still holds. If it no longer holds, mark it no-change-needed with the reason. Apply the findings in the order given. Run only the narrowest test selector that covers your change, never the whole suite.",
      "",
      "Findings:",
      findings,
   ].join("\n")
}

function reviewPrompt(context, changed) {
   return [
      "You are reviewing changes another agent made to the automation program and skills for the site " + context.site + ". Copies of every file as it was before the changes are under " + context.backup_dir + ", with the same absolute path appended (for example " + context.backup_dir + "/Users/name/file.py).",
      "",
      "Changed files:",
      changed.join("\n"),
      "",
      "Diff each changed file against its backup and report every place a change breaks one of these rules. Read only; do not edit anything.",
      "",
      RULES,
   ].join("\n")
}

const context = args
const MAX_PARTITIONS = 8

function runsInChain(partition) {
   const touchesProgram = partition.files.some(file => file.startsWith(context.program_dir))

   return partition.lane ? partition.lane === "chain" : touchesProgram
}

const chainPartitions = context.partitions.filter(runsInChain)
const otherPartitions = context.partitions.filter(partition => !runsInChain(partition))

if (context.partitions.length > MAX_PARTITIONS) {
   throw new Error(context.partitions.length + " partitions in one wave; at most " + MAX_PARTITIONS + " keep the run under 10 agents")
}

for (const partition of otherPartitions) {
   const others = context.partitions.filter(other => other !== partition)
   const clashes = partition.files.filter(file => others.some(other => other.files.includes(file)))

   if (clashes.length > 0) {
      throw new Error(partition.id + " runs in parallel but shares files with another partition: " + clashes.join(", "))
   }
}

log(chainPartitions.length + " partitions run one at a time; " + otherPartitions.length + " run alongside them")

phase("Fix")

async function runChainInOrder() {
   const outputs = []

   for (const partition of chainPartitions) {
      const output = await agent(fixPrompt(context, partition), { label: "fix:" + partition.id, phase: "Fix", schema: FIX_SCHEMA })
      outputs.push({ partition: partition.id, output })
   }

   return outputs
}

const otherRuns = otherPartitions.map(partition => () =>
   agent(fixPrompt(context, partition), { label: "fix:" + partition.id, phase: "Fix", schema: FIX_SCHEMA })
      .then(output => [{ partition: partition.id, output }]))

const grouped = await parallel([runChainInOrder, ...otherRuns])
const fixOutputs = grouped.filter(Boolean).flat()
const failedPartitions = context.partitions.map(partition => partition.id).filter(id => !fixOutputs.some(entry => entry.partition === id && entry.output))

if (failedPartitions.length > 0) {
   log("partitions with no result: " + failedPartitions.join(", "))
}

const results = fixOutputs.filter(entry => entry.output).flatMap(entry => entry.output.results)
const needsFiles = fixOutputs.filter(entry => entry.output).flatMap(entry => entry.output.needs_files)
const changed = [...new Set(results.flatMap(result => result.files_changed))]

phase("Review")
let review = { violations: [], notes: "No files changed, review skipped." }

if (changed.length > 0) {
   review = await agent(reviewPrompt(context, changed), { label: "review:rules", phase: "Review", schema: REVIEW_SCHEMA }) || { violations: [], notes: "Reviewer returned nothing." }
}

return { results, needs_files: needsFiles, failed_partitions: failedPartitions, changed, review }
