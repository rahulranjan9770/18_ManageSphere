from backend.embeddings.text_embedder import TextEmbedder
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

embedder = TextEmbedder()
t1 = "The operating voltage is 220V."
t2 = "Label: Voltage 110V"

e1 = embedder.embed([t1])
e2 = embedder.embed([t2])

sim = cosine_similarity(e1, e2)[0][0]
print(f"Similarity: {sim}")
