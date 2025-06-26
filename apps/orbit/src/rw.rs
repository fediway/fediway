use itertools::Itertools;
use nalgebra_sparse::{coo::CooMatrix, csr::CsrMatrix};
use std::collections::HashMap;
use tokio_postgres::{Client, types::ToSql};

pub async fn get_tag_similarities(db: &Client) -> impl Iterator<Item = (i64, i64, f64)> {
    let query = r#"
    SELECT
        e1.tag_id AS tag1,
        e2.tag_id AS tag2,
        (
            COUNT(distinct e1.account_id) / 
            SQRT(MAX(tf1.engaged_accounts) * MAX(tf2.engaged_accounts))
        ) as cosine_sim
    FROM account_tag_engagements e1
    JOIN account_tag_engagements e2 ON e2.account_id = e1.account_id
    JOIN tag_features tf1 ON tf1.tag_id = e1.tag_id AND tf1.engaged_accounts > 15
    JOIN tag_features tf2 ON tf2.tag_id = e2.tag_id AND tf2.engaged_accounts > 15
    WHERE e1.tag_id < e2.tag_id
    GROUP BY e1.tag_id, e2.tag_id;
    "#;

    db.query(query, &[]).await.unwrap().into_iter().map(|row| {
        let t1: i64 = row.get(0);
        let t2: i64 = row.get(1);
        let sim: f64 = row.get(2);

        (t1, t2, sim)
    })
}

pub async fn get_tag_names(db: &Client, tags: &Vec<i64>) -> HashMap<i64, String> {
    let placeholders: Vec<String> = (1..=tags.len()).map(|i| format!("${}", i)).collect();
    let query = format!(
        "SELECT t.id, t.name FROM tags t WHERE t.id IN ({});",
        placeholders.join(", ")
    );

    let params: Vec<&(dyn ToSql + Sync)> =
        tags.iter().map(|id| id as &(dyn ToSql + Sync)).collect();

    db.query(&query, &params)
        .await
        .unwrap()
        .into_iter()
        .map(|row| {
            let id: i64 = row.get(0);
            let name: String = row.get(1);
            (id, name)
        })
        .collect()
}

pub async fn get_at_matrix(
    db: &Client,
    tag_indices: &HashMap<i64, usize>,
) -> (CsrMatrix<f64>, HashMap<i64, usize>) {
    let placeholders: Vec<String> = (1..=tag_indices.len()).map(|i| format!("${}", i)).collect();
    let query = format!(
        r#"
        SELECT
            e.account_id,
            st.tag_id,
            COUNT(DISTINCT e.status_id) as count
        FROM enriched_status_engagement_events e
        JOIN statuses_tags st ON st.status_id = e.status_id AND st.tag_id IN ({})
        WHERE e.event_time > NOW() - INTERVAL '60 DAYS'
        GROUP BY e.account_id, st.tag_id;
        "#,
        placeholders.join(", ")
    );

    let params: Vec<&(dyn ToSql + Sync)> = tag_indices
        .iter()
        .map(|(id, _)| id as &(dyn ToSql + Sync))
        .collect();

    let rows = db.query(&query, &params).await.unwrap();
    let n_rows = rows
        .iter()
        .map(|r| {
            let account_id: i64 = r.get(0);
            account_id
        })
        .unique()
        .count();
    let n_cols = tag_indices.len();
    let mut matrix = CooMatrix::zeros(n_rows, n_cols);
    let mut account_indices: HashMap<i64, usize> = HashMap::new();

    for row in rows.into_iter() {
        let account_id: i64 = row.get(0);
        let tag_id: i64 = row.get(1);
        let value: i64 = row.get(2);
        let next_idx = account_indices.len();
        let a_idx = *account_indices
            .entry(account_id)
            .or_insert_with(|| next_idx);
        let t_idx = *tag_indices.get(&tag_id).unwrap();

        matrix.push(a_idx, t_idx, value as f64);
    }

    (CsrMatrix::from(&matrix), account_indices)
}

pub async fn get_ta_matrix(
    db: &Client,
    account_indices: &HashMap<i64, usize>,
) -> (CsrMatrix<f64>, HashMap<i64, usize>) {
    let query = r#"
    SELECT
        e.account_id,
        st.tag_id,
        COUNT(DISTINCT e.status_id) as count
    FROM enriched_status_engagement_events e
    JOIN statuses_tags st ON st.status_id = e.status_id
    WHERE e.event_time > NOW() - INTERVAL '60 DAYS'
    GROUP BY e.account_id, st.tag_id;
    "#;

    let rows = db.query(query, &[]).await.unwrap();
    let n_rows = rows
        .iter()
        .filter_map(|r| {
            let account_id: i64 = r.get(0);
            let tag_id: i64 = r.get(1);
            if account_indices.contains_key(&account_id) {
                Some(tag_id)
            } else {
                None
            }
        })
        .unique()
        .count();
    let n_cols = account_indices.len();
    let mut matrix = CooMatrix::zeros(n_rows, n_cols);
    let mut tag_indices: HashMap<i64, usize> = HashMap::new();

    for row in rows.into_iter() {
        let account_id: i64 = row.get(0);

        if let Some(a_idx) = account_indices.get(&account_id) {
            let tag_id: i64 = row.get(1);
            let value: i64 = row.get(2);
            let next_idx = tag_indices.len();
            let t_idx = *tag_indices.entry(tag_id).or_insert(next_idx);

            matrix.push(t_idx, *a_idx, value as f64);
        }
    }

    (CsrMatrix::from(&matrix), tag_indices)
}

pub async fn get_pa_matrix(
    db: &Client,
    account_indices: &HashMap<i64, usize>,
) -> (CsrMatrix<f64>, HashMap<i64, usize>) {
    let query = r#"
    SELECT
        e.account_id,
        e.author_id,
        COUNT(DISTINCT e.status_id) as count
    FROM enriched_status_engagement_events e
    WHERE e.event_time > NOW() - INTERVAL '60 DAYS'
    GROUP BY e.account_id, e.author_id;
    "#;

    let rows = db.query(query, &[]).await.unwrap();
    let n_cols = account_indices.len();
    let n_rows = rows
        .iter()
        .filter_map(|r| {
            let account_id: i64 = r.get(0);
            let producer_id: i64 = r.get(1);
            if account_indices.contains_key(&account_id) {
                Some(producer_id)
            } else {
                None
            }
        })
        .unique()
        .count();
    let mut matrix = CooMatrix::zeros(n_rows, n_cols);
    let mut producer_indices: HashMap<i64, usize> = HashMap::new();

    for row in rows.into_iter() {
        let account_id: i64 = row.get(0);

        if let Some(a_idx) = account_indices.get(&account_id) {
            let producer_id: i64 = row.get(1);
            let value: i64 = row.get(2);
            let next_idx = producer_indices.len();
            let p_idx = *producer_indices.entry(producer_id).or_insert(next_idx);

            matrix.push(p_idx, *a_idx, value as f64);
        }
    }

    (CsrMatrix::from(&matrix), producer_indices)
}

pub async fn get_pt_matrix(
    db: &Client,
    producer_indices: &HashMap<i64, usize>,
    tag_indices: &HashMap<i64, usize>,
) -> CsrMatrix<f64> {
    let placeholders: Vec<String> = (1..=tag_indices.len()).map(|i| format!("${}", i)).collect();
    let query = format!(
        r#"
        SELECT
            e.author_id,
            st.tag_id,
            COUNT(DISTINCT e.status_id) as count
        FROM enriched_status_engagement_events e
        JOIN statuses_tags st ON st.status_id = e.status_id AND st.tag_id IN ({})
        WHERE e.event_time > NOW() - INTERVAL '60 DAYS'
        GROUP BY e.author_id, st.tag_id;
        "#,
        placeholders.join(", ")
    );

    let params: Vec<&(dyn ToSql + Sync)> = tag_indices
        .iter()
        .map(|(id, _)| id as &(dyn ToSql + Sync))
        .collect();

    let rows = db.query(&query, &params).await.unwrap();
    let n_rows = producer_indices.len();
    let n_cols = tag_indices.len();
    let mut matrix = CooMatrix::zeros(n_rows, n_cols);

    for row in rows.into_iter() {
        let producer_id: i64 = row.get(0);

        if let Some(p_idx) = producer_indices.get(&producer_id) {
            let tag_id: i64 = row.get(1);
            if let Some(t_idx) = tag_indices.get(&tag_id) {
                let value: i64 = row.get(2);
                matrix.push(*p_idx, *t_idx, value as f64);
            }
        }
    }

    CsrMatrix::from(&matrix)
}
