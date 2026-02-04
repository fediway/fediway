from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from feast import FeatureService


class Features:
    def get(
        self, entities: list[dict[str, int]], features: "list[str] | FeatureService"
    ) -> pd.DataFrame:
        raise NotImplementedError
