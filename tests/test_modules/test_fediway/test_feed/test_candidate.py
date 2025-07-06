from modules.fediway.feed import Candidate


def test_candidate_init():
    entity = "status_id"
    candidate_id = 123
    score = 0.95
    sources = {("foo", "bar"), ("baz", "boom")}

    candidate = Candidate(entity, candidate_id, score, sources)

    assert candidate.entity == entity
    assert candidate.id == candidate_id
    assert candidate.score == score
    assert candidate.sources == sources
