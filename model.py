# model.py

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

class PriorityModel:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1,2),
            stop_words="english",
            max_features=5000,
            min_df=2
        )
        self.model = LogisticRegression(max_iter=200)

    def train(self, texts, labels):
        X = self.vectorizer.fit_transform(texts)
        self.model.fit(X, labels)

    def predict(self, text):
        X = self.vectorizer.transform([text])
        probs = self.model.predict_proba(X)[0]
        pred = self.model.classes_[probs.argmax()]
        conf = max(probs)
        return pred, conf

priority_model = PriorityModel()