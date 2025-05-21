import pandas as pd

class Features:
    def get(self, entities: list[dict[str, int]], features: list[str]) -> pd.DataFrame:
        raise NotImplementedError
