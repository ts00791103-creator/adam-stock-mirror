// Optional, disabled by default. No Telegram token or stock data belongs here.
const TARGET = "https://api.github.com/repos/ts00791103-creator/adam-mirror-alerts/actions/workflows/entry-alerts.yml/dispatches";
const CRONS = new Set(["57 6 * * MON-FRI", "27 10 * * MON-FRI"]);

export async function dispatchScheduled(event, env, fetchImpl = fetch) {
  if (env.DISPATCH_ENABLED !== "true") return {status: "disabled"};
  if (!CRONS.has(event.cron)) throw new Error("Unrecognized backup schedule");
  const date = new Date(event.scheduledTime);
  if (!Number.isFinite(date.getTime())) throw new Error("Invalid scheduled time");
  if ([0, 6].includes(date.getUTCDay())) return {status: "weekend_skipped"};
  if (!env.GITHUB_ACTIONS_TOKEN) throw new Error("Missing dispatch credential");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10000);
  let response;
  try {
    response = await fetchImpl(TARGET, {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: "Bearer " + env.GITHUB_ACTIONS_TOKEN,
        "X-GitHub-Api-Version": "2026-03-10",
        "User-Agent": "adam-mirror-backup-scheduler",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ref: "main", inputs: {mode: "send"}}),
      signal: controller.signal
    });
  } catch {
    throw new Error("GitHub dispatch connection failed; no automatic retry");
  } finally {
    clearTimeout(timer);
  }
  if (![200, 204].includes(response.status)) {
    throw new Error("GitHub dispatch was not accepted (HTTP " + response.status + ")");
  }
  return {status: "dispatch_accepted"};
}

export default {
  scheduled(event, env, ctx) {
    ctx.waitUntil(dispatchScheduled(event, env));
  },
  fetch() {
    return new Response("Not found", {status: 404});
  }
};
