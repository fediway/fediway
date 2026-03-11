#[derive(Debug, Clone)]
pub struct Candidate<Item> {
    pub item: Item,
    pub score: f64,
    pub source: &'static str,
}

impl<Item> Candidate<Item> {
    pub fn new(item: Item, source: &'static str) -> Self {
        Self {
            item,
            score: 0.0,
            source,
        }
    }
}
