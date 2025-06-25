
use bloomfilter::Bloom;
use linked_hash_map::LinkedHashMap;
use std::collections::VecDeque;
use std::hash::{Hash, Hasher};

#[derive(Debug, Clone, Eq)]
pub struct SortedPair(i64, i64);

impl SortedPair {
    pub fn new(a: i64, b: i64) -> Self {
        if a <= b {
            SortedPair(a, b)
        } else {
            SortedPair(b, a)
        }
    }
}

// Equality depends only on sorted values
impl PartialEq for SortedPair {
    fn eq(&self, other: &Self) -> bool {
        self.0 == other.0 && self.1 == other.1
    }
}

// Hash implementation uses sorted values
impl Hash for SortedPair {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.0.hash(state);
        self.1.hash(state);
    }
}

pub struct BloomCounter<T> {
    bloom: Bloom<T>,
    counter: usize,
}

impl<T> BloomCounter<T>
where T: Hash {

    /// Create a new BloomCounter with specified number of items and false 
    /// positive rate.
    pub fn new(items: usize, fp_rate: f64) -> Self {
        Self { 
            bloom: Bloom::new_for_fp_rate(items, fp_rate).unwrap(),
            counter: 0
        }
    }

    /// Increment counter if the key hasn't been seen before.
    pub fn increment(&mut self, key: &T) -> usize {
        if !self.bloom.check(key) {
            self.bloom.set(key);
            self.counter += 1;
        }
        self.counter
    }


    /// Check if a key might have been seen before.
    pub fn contains(&self, key: &T) -> bool {
        self.bloom.check(key)
    }

    /// Reset the counter and bloom filter
    pub fn reset(&mut self) {
        self.bloom.clear();
        self.counter = 0;
    }
}

pub struct HashSetDeque<T: Eq + Hash> {
    map: LinkedHashMap<T, ()>,
    capacity: usize,
}

impl<T: Eq + Hash> HashSetDeque<T> {
    /// Creates a new buffer with the given maximum capacity
    pub fn new(capacity: usize) -> Self {
        assert!(capacity > 0, "Capacity must be positive");
        HashSetDeque {
            map: LinkedHashMap::with_capacity(capacity),
            capacity,
        }
    }

    /// Adds an item to the buffer
    pub fn push(&mut self, item: T) {
        // Remove existing entry to update its position
        self.map.remove(&item);
        
        // Remove oldest item if full
        if self.map.len() == self.capacity {
            self.pop_front();
        }
        
        // Add new item to the back
        self.map.insert(item, ());
    }

    /// Removes and returns the oldest item
    pub fn pop_front(&mut self) -> Option<T> {
        self.map.pop_front().map(|(k, _)| k)
    }

    /// Removes and returns the newest item
    pub fn pop_back(&mut self) -> Option<T> {
        self.map.pop_back().map(|(k, _)| k)
    }

    /// Checks if an item exists in the buffer
    pub fn contains(&self, item: &T) -> bool {
        self.map.contains_key(item)
    }

    /// Returns the number of items
    pub fn len(&self) -> usize {
        self.map.len()
    }

    /// Checks if the buffer is empty
    pub fn is_empty(&self) -> bool {
        self.map.is_empty()
    }

    /// Returns an iterator from oldest to newest
    pub fn iter(&self) -> impl Iterator<Item = &T> {
        self.map.keys()
    }
}