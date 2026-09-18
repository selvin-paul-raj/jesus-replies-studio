/**
 * ============================================================================
 * LIST BUFFER CHANNELS -- one-off lookup for the GraphQL channelId of each
 * connected social profile (e.g. Instagram). Buffer's GraphQL API uses
 * different ids than the old REST "profile_ids", so BUFFER_INSTAGRAM_CHANNEL_ID
 * needs to be re-checked against this output after the REST -> GraphQL
 * migration (see scripts/publish-buffer.ts). Run once locally:
 *   npx tsx --env-file=.env scripts/list-buffer-channels.ts
 * ============================================================================
 */

const BUFFER_API_BASE = "https://api.buffer.com";

async function graphql<T>(query: string): Promise<T> {
  const apiKey = process.env.BUFFER_API_KEY;
  if (!apiKey) throw new Error("BUFFER_API_KEY is not set");

  const res = await fetch(BUFFER_API_BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({ query }),
  });

  const json = await res.json();
  if (!res.ok || json.errors) {
    throw new Error(`Buffer GraphQL error: ${JSON.stringify(json.errors ?? json)}`);
  }
  return json.data;
}

async function main(): Promise<void> {
  const { account } = await graphql<{ account: { organizations: { id: string }[] } }>(
    `query { account { organizations { id } } }`
  );

  for (const org of account.organizations) {
    const { channels } = await graphql<{ channels: { id: string; name: string; service: string }[] }>(
      `query { channels(input: { organizationId: ${JSON.stringify(org.id)} }) { id name service } }`
    );
    console.log(`Organization ${org.id}:`);
    for (const channel of channels) {
      console.log(`  ${channel.service.padEnd(12)} ${channel.name.padEnd(30)} id=${channel.id}`);
    }
  }
}

main().catch((error) => {
  console.error("[list-buffer-channels] FAILED:", error instanceof Error ? error.message : error);
  process.exit(1);
});
