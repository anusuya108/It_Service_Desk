# model.py

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


class PriorityModel:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=3000
        )
        self.model = LogisticRegression(max_iter=200)

    def train(self, texts, labels):
        X = self.vectorizer.fit_transform(texts)
        self.model.fit(X, labels)

    def predict(self, text):
        X = self.vectorizer.transform([text])
        pred = self.model.predict(X)[0]
        return pred


# instance
priority_model = PriorityModel()