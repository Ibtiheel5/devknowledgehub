import { apiGet } from "./api";

export function getAgentRuns(limit = 50) {
  return apiGet(`/api/v1/mlops/agent-runs?limit=${limit}`);
}
