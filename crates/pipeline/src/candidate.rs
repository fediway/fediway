#[derive(Debug, Clone)]
pub struct Candidate<T> {
    pub item: T,
    pub score: f64,
    pub source: &'static str,
}

impl<T> Candidate<T> {
    pub fn new(item: T, source: &'static str) -> Self {
        Self {
            item,
            score: 0.0,
            source,
        }
    }
}
