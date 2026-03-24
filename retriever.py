# retriever.py

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

df = pd.read_csv("data/data.csv")

vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(df["text"])

def retrieve(text):
    q = vectorizer.transform([text])
    sim = cosine_similarity(q, X)[0]
    idx = sim.argmax()
    return df.iloc[idx]["text"], round(sim[idx],2)