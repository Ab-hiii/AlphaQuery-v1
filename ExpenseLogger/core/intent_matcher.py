import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class IntentMatcher:

    KEYWORD_RULES = [
        (["vs", "versus", "compare"],                           "compare_periods"),
        (["biggest expense", "highest spending", "most spent",
          "top category", "where do i spend", "which category"], "top_category"),
        (["average", "avg", "mean spend"],                      "average_spend"),
        (["show ", "list ", "display ", "find all", "get all"], "list_transactions"),
        (["how much", "total spend", "total expense",
          "total on", "total for", "total ",
          "what did i spend", "what have i spent",
          "how much have i"],                                    "total_spend"),
    ]

    DEFAULT_INTENT = "list_transactions"

    def __init__(self, templates_path="data/intent_templates.json"):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        with open(templates_path) as f:
            self.intent_templates = json.load(f)

        all_phrases = []
        self.phrase_to_intent = []

        for intent, phrases in self.intent_templates.items():
            for p in phrases:
                all_phrases.append(p)
                self.phrase_to_intent.append(intent)

        self.template_embeddings = self.model.encode(all_phrases)

    def _keyword_match(self, query_lower: str):
        for keywords, intent in self.KEYWORD_RULES:
            if any(kw in query_lower for kw in keywords):
                return intent
        return None

    def match_intent(self, query: str) -> dict:
        query_lower = query.lower()

        keyword_intent = self._keyword_match(query_lower)

        query_emb = self.model.encode([query_lower])
        sims = cosine_similarity(query_emb, self.template_embeddings)[0]

        best_idx = int(np.argmax(sims))
        semantic_intent = self.phrase_to_intent[best_idx]
        best_score = float(sims[best_idx])

        sims_copy = sims.copy()
        sims_copy[best_idx] = -1
        second_score = float(np.max(sims_copy))
        margin = round(best_score - second_score, 3)

        if keyword_intent:
            final_intent = keyword_intent
            source = "keyword"
            if keyword_intent != semantic_intent:
                best_score = max(best_score, 0.60)
        elif margin >= 0.05:
            final_intent = semantic_intent
            source = "semantic"
        else:
            final_intent = self.DEFAULT_INTENT
            source = "default"

        return {
            "intent": final_intent,
            "score":  round(best_score, 3),
            "margin": margin,
            "source": source
        }
