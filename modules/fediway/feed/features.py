import pandas as pd
from feast import FeatureService


class Features:
    def get(
        self, entities: list[dict[str, int]], features: list[str] | FeatureService
    ) -> pd.DataFrame:
        raise NotImplementedError
