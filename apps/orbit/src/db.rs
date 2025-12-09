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
    for tags in communities
        .tags
        .keys()
        .cloned()
        .collect::<Vec<i64>>()
        .chunks(2)
    {
        println!("tags: {:?}", tags);

        let placeholders: Vec<String> = (1..=tags.len()).map(|i| format!("${}", i)).collect();
        let query = format!(
            r#"
            WITH engagements AS (
                SELECT 
                    f.account_id,
                    f.status_id,
                    0 AS type,
                    f.id as entity_id,
                    f.created_at AS event_time
                FROM favourites f

                UNION

                SELECT 
                    s.account_id,
                    s.reblog_of_id AS status_id,
                    1 AS type,
                    s.id as entity_id,
                    s.created_at AS event_time
                FROM statuses s
                WHERE s.reblog_of_id IS NOT NULL

                UNION

                SELECT
                    s.account_id,
                    s.in_reply_to_id AS status_id,
                    2 AS type,
                    s.id as entity_id,
                    s.created_at AS event_time
                FROM statuses s
                WHERE s.in_reply_to_id IS NOT NULL

                UNION

                SELECT
                    v.account_id,
                    p.status_id as status_id,
                    3 AS type,
                    v.id as entity_id,
                    v.created_at AS event_time
                FROM poll_votes v
                JOIN polls p ON p.id = v.poll_id

                UNION

                SELECT
                    account_id,
                    status_id,
                    4 AS type,
                    id as entity_id,
                    created_at AS event_time
                FROM bookmarks

                UNION

                SELECT
                    account_id,
                    quoted_status_id as status_id,
                    5 AS type,
                    status_id as entity_id,
                    created_at AS event_time
                FROM quotes
                WHERE state = 1
            )
            SELECT 
                e.account_id,
                st.tag_id,
                COUNT(*) AS interactions
            FROM 
                statuses_tags st
            JOIN 
                engagements e ON e.status_id = st.status_id
            WHERE st.tag_id IN ({})
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
