import { apiGet, apiPost } from "./api";

export function getAgentRuns(limit = 50) {
  return apiGet(`/api/v1/mlops/agent-runs?limit=${limit}`);
}

export function getMonitoring(repoName, days = 7) {
  const params = new URLSearchParams({ days: String(days) });
  if (repoName) params.set("repo_name", repoName);
  return apiGet(`/api/v1/mlops/monitoring?${params.toString()}`);
}

export function getModels(repoName) {
  const query = repoName ? `?repo_name=${encodeURIComponent(repoName)}` : "";
  return apiGet(`/api/v1/mlops/models${query}`);
}

export function getQuality(repoName, modelName) {
  const params = new URLSearchParams();
  if (repoName) params.set("repo_name", repoName);
  if (modelName) params.set("model_name", modelName);
  const query = params.toString();
  return apiGet(`/api/v1/mlops/quality${query ? `?${query}` : ""}`);
}

export function recordMetric(name, value, labels = {}) {
  return apiPost("/api/v1/mlops/metrics", { name, value, labels });
}
