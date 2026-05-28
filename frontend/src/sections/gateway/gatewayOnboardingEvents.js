const DEFAULT_GATEWAY_ID = "default";

const compactMetadata = (metadata) =>
  Object.fromEntries(
    Object.entries(metadata).filter(
      ([, value]) => value !== undefined && value !== null && value !== "",
    ),
  );

const safeKeyPart = (value, fallback) =>
  String(value || fallback)
    .replace(/\s+/g, "-")
    .slice(0, 56);

const fallbackChainsForRouting = (routing = {}) =>
  routing.model_fallbacks || routing.modelFallbacks || {};

export const buildGatewayFallbackPolicyCreatedPayload = ({
  gatewayId = DEFAULT_GATEWAY_ID,
  requestId,
  routing,
  source = "gateway_fallbacks_onboarding",
} = {}) => {
  const fallbackChains = fallbackChainsForRouting(routing);
  const chainCount = Object.keys(fallbackChains).filter(Boolean).length;

  return {
    eventName: "gateway_policy_created",
    primaryPath: "gateway",
    stage: "add_gateway_policy",
    source,
    artifactType: "gateway_policy",
    artifactId: safeKeyPart(requestId || gatewayId, "fallback-config"),
    metadata: compactMetadata({
      gateway_id: gatewayId || DEFAULT_GATEWAY_ID,
      request_id: requestId,
      policy_type: "fallback",
      policy_id: requestId ? `fallback:${requestId}` : "fallback",
      gateway_synced: true,
      fallback_chain_count: chainCount,
      fallback_enabled: Boolean(
        routing?.fallback_enabled ?? routing?.fallbackEnabled ?? true,
      ),
    }),
    idempotencyKey: [
      "gateway_policy_created",
      "fallback",
      safeKeyPart(requestId, "no-request"),
      safeKeyPart(gatewayId, DEFAULT_GATEWAY_ID),
    ].join(":"),
    isSample: false,
  };
};
