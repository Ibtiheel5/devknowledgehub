import { apiPost } from "./api";

export function searchAgent(repoName, question, maxResults = 10) {
  return apiPost("/api/v1/agents/search", {
    repo_name: repoName,
    question,
    max_results: maxResults
  });
}

export function askAgent(repoName, question, topK = 8) {
  return apiPost("/api/v1/agents/ask", {
    repo_name: repoName,
    question,
    top_k: topK
  });
}
