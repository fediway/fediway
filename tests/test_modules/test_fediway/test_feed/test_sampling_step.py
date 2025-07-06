import pytest
import numpy as np
import pandas as pd

from modules.fediway.feed import CandidateList, Sampler, Features
from modules.fediway.feed.sampling import TopKSampler
from modules.fediway.feed.steps import SamplingStep
from modules.fediway.heuristics import Heuristic, DiversifyHeuristic


class MockFeatureService(Features):
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.get_calls = []

    async def get(self, entity_rows, features):
        self.get_calls.append((entity_rows, features))

        entities = list(entity_rows[0].keys())
        df = self.data[features + entities]

        for e in entities:
            df = df[df[e].isin([r[e] for r in entity_rows])]

        return df


@pytest.fixture
def mock_sampler():
    return TopKSampler()


@pytest.fixture
def mock_heuristic():
    return DiversifyHeuristic(by="status:author_id", penalty=0.1)


@pytest.fixture
def mock_feature_service():
    return MockFeatureService(
        [
            {
                "status_id": 101,
                "status:author_id": 1,
                "status:engagements": 0.8,
                "status:age": 0.9,
            },
            {
                "status_id": 102,
                "status:author_id": 1,
                "status:engagements": 0.7,
                "status:age": 0.8,
            },
            {
                "status_id": 103,
                "status:author_id": 2,
                "status:engagements": 0.6,
                "status:age": 0.7,
            },
            {
                "status_id": 104,
                "status:author_id": 2,
                "status:engagements": 0.5,
                "status:age": 0.6,
            },
            {
                "status_id": 105,
                "status:author_id": 3,
                "status:engagements": 0.4,
                "status:age": 0.5,
            },
        ]
    )


@pytest.fixture
def sample_candidates():
    candidates = CandidateList("status_id")

    candidates.append(101, 0.9, "timeline", "user_feed")
    candidates.append(102, 0.8, "trending", "trending_feed")
    candidates.append(103, 0.7, "recommendations", "ml_recs")
    candidates.append(104, 0.6, "following", "social_graph")
    candidates.append(105, 0.5, "hashtags", "hashtag_feed")

    return candidates


def test_sampling_step_init(mock_sampler, mock_feature_service):
    step = SamplingStep(
        sampler=mock_sampler, feature_service=mock_feature_service, entity="status_id"
    )

    assert step.entity == "status_id"
    assert step.n == float("inf")
    assert step.unique is True
    assert len(step.heuristics) == 0
    assert len(step.seen) == 0
    assert step.sampler == mock_sampler
    assert step.feature_service == mock_feature_service


def test_sampling_step_init_with_params(
    mock_sampler, mock_feature_service, mock_heuristic
):
    step = SamplingStep(
        sampler=mock_sampler,
        feature_service=mock_feature_service,
        entity="account_id",
        n=3,
        heuristics=[mock_heuristic],
        unique=False,
    )

    assert step.entity == "account_id"
    assert step.n == 3
    assert step.unique is False
    assert len(step.heuristics) == 1
    assert step.heuristics[0] == mock_heuristic


def test_get_params(mock_sampler, mock_feature_service, mock_heuristic):
    step = SamplingStep(
        sampler=mock_sampler,
        feature_service=mock_feature_service,
        entity="status_id",
        n=5,
        heuristics=[mock_heuristic],
        unique=False,
    )

    params = step.get_params()

    assert params["n"] == 5
    assert params["unique"] is False
    assert len(params["heuristics"]) == 1
    assert params["heuristics"][0]["name"] == "DiversifyHeuristic"
    assert params["sampler"]["name"] == "TopKSampler"


def test_get_state_empty(mock_sampler, mock_feature_service):
    step = SamplingStep(
        sampler=mock_sampler, feature_service=mock_feature_service, entity="status_id"
    )

    state = step.get_state()

    assert state["seen"] == []
    assert state["heuristics"] == []


def test_get_state_with_data(mock_sampler, mock_feature_service, mock_heuristic):
    step = SamplingStep(
        sampler=mock_sampler,
        feature_service=mock_feature_service,
        entity="status_id",
        heuristics=[mock_heuristic],
    )

    step.seen.add(101)
    step.seen.add(102)

    state = step.get_state()

    assert set(state["seen"]) == {101, 102}
    assert len(state["heuristics"]) == 1


def test_set_state(mock_sampler, mock_feature_service, mock_heuristic):
    step = SamplingStep(
        sampler=mock_sampler,
        feature_service=mock_feature_service,
        entity="status_id",
        heuristics=[mock_heuristic],
    )

    state = {
        "seen": [101, 102, 103],
        "heuristics": [{"update_seen_calls": [(101, {})]}],
    }

    step.set_state(state)

    assert step.seen == {101, 102, 103}
    assert len(step.heuristics) == 1
