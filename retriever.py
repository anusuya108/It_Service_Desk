# retriever.py

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# load dataset
df = pd.read_csv("data/data.csv")

vectorizer = TfidfVectorizer(stop_words="english")
X = vectorizer.fit_transform(df["text"])


def retrieve_similar(query):
    q_vec = vectorizer.transform([query])
    similarities = cosine_similarity(q_vec, X)[0]

    idx = similarities.argmax()

    return {
        "text": df.iloc[idx]["text"],
        "score": round(similarities[idx], 2)
    }