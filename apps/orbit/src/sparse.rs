use crate::types::FastHashMap;

use petgraph::algo::FloatMeasure;
use sprs::CsVec;
use std::ops::{AddAssign, Mul, MulAssign};

#[derive(Clone)]
pub struct SparseVec(pub CsVec<f64>);

impl SparseVec {
    pub fn new(dim: usize, indices: Vec<usize>, values: Vec<f64>) -> Self {
        Self(CsVec::new(dim, indices, values))
    }

    pub fn empty(dim: usize) -> Self {
        Self(CsVec::empty(dim))
    }

    pub fn to_owned(&self) -> Self {
        SparseVec(self.0.to_owned())
    }

    pub fn normalize(&mut self) {
        let norm: f64 = self.0.norm(f64::infinite());

        if norm > 0.0 && !norm.is_nan() {
            *self *= 1.0 / norm;
        }
    }

    pub fn is_zero(&self) -> bool {
        self.0.data().is_empty()
    }

    /// Keep only the top `n` elements by absolute value
    pub fn keep_top_n(&mut self, n: usize) {
        // Get mutable access to indices and data
        let (indices, data) = (self.0.indices(), self.0.data());

        // Create vector of (absolute value, original value, index)
        let mut entries: Vec<_> = indices
            .iter()
            .zip(data.iter())
            .map(|(&idx, &val)| (val.abs(), val, idx))
            .collect();

        // Sort by absolute value descending
        entries.sort_unstable_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));

        // Keep only top n entries
        entries.truncate(n);

        // Sort by index to maintain sparse vector invariant
        entries.sort_unstable_by_key(|&(_, _, idx)| idx);

        // Split back into indices and values
        let (new_indices, new_data): (Vec<_>, Vec<_>) =
            entries.into_iter().map(|(_, val, idx)| (idx, val)).unzip();

        // Create new sparse vector
        self.0 = CsVec::new(self.0.dim(), new_indices, new_data);
    }

    pub fn set_entries(&mut self, mut indices: Vec<usize>, value: f64) {
        let mut entries: FastHashMap<usize, f64> = self.0.iter().map(|(i, &v)| (i, v)).collect();

        // Override/insert new values
        for idx in indices {
            if value == 0.0 {
                entries.remove(&idx);
            } else {
                entries.insert(idx, value);
            }
        }

        // Convert back to sorted vectors
        let mut pairs: Vec<(usize, f64)> = entries.into_iter().collect();
        pairs.sort_unstable_by_key(|&(idx, _)| idx);

        let (new_indices, new_data): (Vec<_>, Vec<_>) = pairs.into_iter().unzip();
        self.0 = CsVec::new(self.0.dim(), new_indices, new_data);
    }
}

impl Mul<f64> for SparseVec {
    type Output = Self;

    fn mul(mut self, rhs: f64) -> Self::Output {
        self *= rhs;
        self
    }
}

impl MulAssign<f64> for SparseVec {
    fn mul_assign(&mut self, rhs: f64) {
        self.0 *= rhs;
    }
}

impl AddAssign<&SparseVec> for SparseVec {
    fn add_assign(&mut self, rhs: &SparseVec) {
        self.0 = (&self.0 + &rhs.0).to_owned();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_set_entries_basic() {
        let mut vec = SparseVec::new(10, vec![1, 3, 5], vec![1.0, 2.0, 3.0]);

        // Set new entries
        vec.set_entries(vec![7, 9], 5.0);

        let indices: Vec<usize> = vec.0.indices().to_vec();
        let data: Vec<f64> = vec.0.data().to_vec();

        assert_eq!(indices, vec![1, 3, 5, 7, 9]);
        assert_eq!(data, vec![1.0, 2.0, 3.0, 5.0, 5.0]);
    }

    #[test]
    fn test_set_entries_override_existing() {
        let mut vec = SparseVec::new(10, vec![1, 3, 5], vec![1.0, 2.0, 3.0]);

        // Override existing entry at index 3
        vec.set_entries(vec![3], 10.0);

        let indices: Vec<usize> = vec.0.indices().to_vec();
        let data: Vec<f64> = vec.0.data().to_vec();

        assert_eq!(indices, vec![1, 3, 5]);
        assert_eq!(data, vec![1.0, 10.0, 3.0]);
    }

    #[test]
    fn test_set_entries_mixed() {
        let mut vec = SparseVec::new(10, vec![2, 4, 6], vec![1.0, 2.0, 3.0]);

        // Mix of new and existing indices
        vec.set_entries(vec![0, 4, 8], 7.0);

        let indices: Vec<usize> = vec.0.indices().to_vec();
        let data: Vec<f64> = vec.0.data().to_vec();

        assert_eq!(indices, vec![0, 2, 4, 6, 8]);
        assert_eq!(data, vec![7.0, 1.0, 7.0, 3.0, 7.0]);
    }

    #[test]
    fn test_set_entries_unsorted_input() {
        let mut vec = SparseVec::new(10, vec![1, 5], vec![1.0, 2.0]);

        // Unsorted input indices
        vec.set_entries(vec![7, 3, 9], 4.0);

        let indices: Vec<usize> = vec.0.indices().to_vec();
        let data: Vec<f64> = vec.0.data().to_vec();

        // Should be sorted in output
        assert_eq!(indices, vec![1, 3, 5, 7, 9]);
        assert_eq!(data, vec![1.0, 4.0, 2.0, 4.0, 4.0]);
    }

    #[test]
    fn test_set_entries_duplicates_in_input() {
        let mut vec = SparseVec::new(10, vec![1, 5], vec![1.0, 2.0]);

        // Duplicate indices in input
        vec.set_entries(vec![3, 3, 7], 5.0);

        let indices: Vec<usize> = vec.0.indices().to_vec();
        let data: Vec<f64> = vec.0.data().to_vec();

        // Should handle duplicates (note: current implementation may keep both)
        assert_eq!(indices[0], 1);
        assert_eq!(data[0], 1.0);
        assert!(indices.contains(&3));
        assert!(indices.contains(&5));
        assert!(indices.contains(&7));
    }

    #[test]
    fn test_set_entries_empty_vec() {
        let mut vec = SparseVec::empty(10);

        vec.set_entries(vec![2, 5, 8], 3.0);

        let indices: Vec<usize> = vec.0.indices().to_vec();
        let data: Vec<f64> = vec.0.data().to_vec();

        assert_eq!(indices, vec![2, 5, 8]);
        assert_eq!(data, vec![3.0, 3.0, 3.0]);
    }

    #[test]
    fn test_set_entries_preserves_dimension() {
        let mut vec = SparseVec::new(20, vec![1, 5], vec![1.0, 2.0]);

        vec.set_entries(vec![10, 15], 7.0);

        assert_eq!(vec.0.dim(), 20);
    }
}
