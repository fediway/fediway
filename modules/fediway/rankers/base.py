
class Ranker():
    features: list[str] = []

    @property
    def name(self) -> str:
        return self.__name__

    def predict(self, X):
        raise NotImplementedError