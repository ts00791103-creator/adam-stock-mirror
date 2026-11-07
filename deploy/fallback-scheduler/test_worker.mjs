import assert from "node:assert/strict";
import worker, {dispatchScheduled} from "./worker.mjs";
const event = {cron: "57 6 * * MON-FRI", scheduledTime: Date.UTC(2026,10,6,6,57)};
const env = {DISPATCH_ENABLED: "true", GITHUB_ACTIONS_TOKEN: "fake-test-token"};
let calls = [];
const fake = async (url, init) => {calls.push({url, init}); return {status: 200};};
assert.equal((await dispatchScheduled(event, {}, fake)).status, "disabled");
assert.equal(calls.length, 0);
assert.equal((await dispatchScheduled(event, env, fake)).status, "dispatch_accepted");
assert.equal(calls.length, 1);
assert.equal(calls[0].url, "https://api.github.com/repos/ts00791103-creator/adam-mirror-alerts/actions/workflows/entry-alerts.yml/dispatches");
assert.deepEqual(JSON.parse(calls[0].init.body), {ref:"main", inputs:{mode:"send"}});
assert.equal(calls[0].init.headers["X-GitHub-Api-Version"], "2026-03-10");
await assert.rejects(dispatchScheduled(event, {DISPATCH_ENABLED:"true"}, fake), /Missing dispatch/);
assert.equal((await dispatchScheduled({...event,scheduledTime:Date.UTC(2026,10,7)},env,fake)).status,"weekend_skipped");
await assert.rejects(dispatchScheduled({...event,cron:"* * * * *"},env,fake),/Unrecognized/);
await assert.rejects(dispatchScheduled(event,env,async()=>({status:403})),/HTTP 403/);
try {
  await dispatchScheduled(event,env,async()=>{throw new Error("fake-test-token https://private.example");});
  assert.fail("Expected sanitized exception");
} catch (error) {
  assert(!error.message.includes("fake-test-token"));
  assert(!error.message.includes("private.example"));
}
assert.equal((await worker.fetch()).status,404);
console.log("8 backup scheduler checks passed; all HTTP calls mocked.");
