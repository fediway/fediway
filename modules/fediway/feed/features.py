from feast import FeatureService
import pandas as pd


class Features:
    def get(
        self, entities: list[dict[str, int]], features: list[str] | FeatureService
    ) -> pd.DataFrame:
        raise NotImplementedError
