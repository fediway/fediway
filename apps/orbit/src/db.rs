use crate::{
    communities::Communities,
    types::{FastHashMap, FastHashSet},
};
use itertools::Itertools;
use nalgebra_sparse::{coo::CooMatrix, csr::CsrMatrix};
use tokio_postgres::{Client, types::ToSql};

pub async fn get_at_matrix(
    db: &Client,
    communities: &Communities,
) -> (CsrMatrix<f64>, FastHashMap<i64, usize>) {
    let mut entries = Vec::new();
    let mut n = 0;
    for tags in communities
        .tags
        .keys()
        .cloned()
        .collect::<Vec<i64>>()
        .chunks(10)
    {
        n += tags.len();

        println!("{:?}/{:?}", n, communities.dim);

        let placeholders: Vec<String> = (1..=tags.len()).map(|i| format!("${}", i)).collect();
        let query = format!(
            r#"
            WITH target_statuses AS (
                SELECT status_id
                FROM statuses_tags
                WHERE tag_id IN ({})
            )
            SELECT 
                e.account_id,
                st.tag_id,
                COUNT(*) AS interactions
            FROM 
                target_statuses ts
            JOIN 
                statuses_tags st ON ts.status_id = st.status_id
            JOIN (
                SELECT 
                    f.account_id,
                    f.status_id
                FROM favourites f
                WHERE f.status_id IN (SELECT status_id FROM target_statuses)
                UNION ALL
                SELECT 
                    s.account_id,
                    s.reblog_of_id AS status_id
                FROM statuses s
                WHERE s.reblog_of_id IN (SELECT status_id FROM target_statuses)
                UNION ALL
                SELECT
                    s.account_id,
                    s.in_reply_to_id AS status_id
                FROM statuses s
                WHERE s.in_reply_to_id IN (SELECT status_id FROM target_statuses)
                UNION ALL
                SELECT
                    v.account_id,
                    p.status_id as status_id
                FROM poll_votes v
                JOIN polls p ON p.id = v.poll_id
                WHERE p.status_id IN (SELECT status_id FROM target_statuses)
                UNION ALL
                SELECT
                    b.account_id,
                    b.status_id
                FROM bookmarks b
                WHERE b.status_id IN (SELECT status_id FROM target_statuses)
                UNION ALL
                SELECT
                    q.account_id,
                    q.quoted_status_id as status_id
                FROM quotes q
                WHERE state = 1 
                AND q.status_id IN (SELECT status_id FROM target_statuses)
            ) e ON e.status_id = st.status_id
            GROUP BY 
                e.account_id,
                st.tag_id;
            "#,
            placeholders.join(", ")
        );

        let params: Vec<&(dyn ToSql + Sync)> =
            tags.iter().map(|id| id as &(dyn ToSql + Sync)).collect();
        let rows = db.query(&query, &params).await.unwrap();
        for row in rows {
            let account_id: i64 = row.get(0);
            let tag_id: i64 = row.get(1);
            let value: i64 = row.get(2);

            entries.push((account_id, tag_id, value));
        }
    }

    println!("{}", entries.len());
    std::process::exit(1);

    let n_rows = entries.iter().map(|(a, _, _)| a).unique().count();
    let n_cols = communities.dim;
    let mut matrix = CooMatrix::zeros(n_rows, n_cols);
    let mut account_indices: FastHashMap<i64, usize> = FastHashMap::default();

    for (account_id, tag_id, value) in entries.into_iter() {
        let next_idx = account_indices.len();
        let a_idx = *account_indices
            .entry(account_id)
            .or_insert_with(|| next_idx);
        let t_idx = *communities.tags.get(&tag_id).unwrap();

        matrix.push(a_idx, t_idx, value as f64);
    }

    (CsrMatrix::from(&matrix), account_indices)
}
