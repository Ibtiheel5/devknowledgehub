import { apiGet, apiPost } from "./api";

export function indexRepository(repoName, gitUrl) {
  return apiPost("/api/v1/rag/index", {
    repo_name: repoName,
    git_url: gitUrl
  });
}

export function searchRag(repoName, question, topK = 8) {
  return apiPost("/api/v1/rag/search", {
    repo_name: repoName,
    question,
    top_k: topK
  });
}

export function getRagStats(repoName) {
  return apiGet(`/api/v1/rag/${encodeURIComponent(repoName)}/stats`);
}
