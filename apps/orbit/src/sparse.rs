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
