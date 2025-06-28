use ahash::RandomState;
use dashmap::DashMap;
use std::collections::{HashMap, HashSet};

pub type FastHashMap<K, V> = HashMap<K, V, RandomState>;
pub type FastHashSet<K> = HashSet<K, RandomState>;
pub type FastDashMap<K, V> = DashMap<K, V, RandomState>;
