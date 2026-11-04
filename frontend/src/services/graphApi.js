import { apiGet, apiPost } from "./api";

function repoBase(repoName) {
  return `/api/v1/graph/${encodeURIComponent(repoName)}`;
}

export function getHealth() {
  return apiGet("/health");
}

export function getRepoStats(repoName) {
  return apiGet(`${repoBase(repoName)}/stats`);
}

export function getRepoCalls(repoName, limit = 200) {
  return apiGet(`${repoBase(repoName)}/calls?limit=${limit}`);
}

export function getRepoSymbols(repoName, limit = 50) {
  return apiGet(`${repoBase(repoName)}/symbols?limit=${limit}`);
}

export function getCallers(repoName, qualifiedName) {
  return apiGet(
    `${repoBase(repoName)}/callers?qualified_name=${encodeURIComponent(qualifiedName)}`
  );
}

export function getCallees(repoName, qualifiedName) {
  return apiGet(
    `${repoBase(repoName)}/callees?qualified_name=${encodeURIComponent(qualifiedName)}`
  );
}

export function buildGraph(repoName, gitUrl) {
  return apiPost("/api/v1/graph/build", { repo_name: repoName, git_url: gitUrl });
}

export function analyzeRepository(gitUrl) {
  return apiPost("/api/v1/repositories/analyze", { git_url: gitUrl });
}
