use crate::kafka::{EngagementEvent, StatusEvent};
use crate::types::{FastHashMap, FastHashSet};
use itertools::Itertools;
use nalgebra_sparse::{coo::CooMatrix, csr::CsrMatrix};
use std::time::SystemTime;
use tokio_postgres::{Client, types::ToSql};

pub async fn get_tag_similarities(db: &Client) -> impl Iterator<Item = (i64, i64, f64)> {
    let query = r#"
    SELECT
        e1.tag_id AS tag1,
        e2.tag_id AS tag2,
        (
            COUNT(distinct e1.account_id) / 
            SQRT(MAX(t1.num_engaged_accounts) * MAX(t2.num_engaged_accounts))
        ) as cosine_sim
    FROM orbit_account_tag_engagements e1
    JOIN orbit_account_tag_engagements e2 ON e2.account_id = e1.account_id
    JOIN orbit_tag_performance t1 ON t1.tag_id = e1.tag_id AND t1.num_authors > 2 AND t1.num_engaged_accounts >= 10
    JOIN orbit_tag_performance t2 ON t2.tag_id = e2.tag_id AND t1.num_authors > 2 AND t2.num_engaged_accounts >= 10
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

pub async fn get_tag_names(db: &Client, tags: &[i64]) -> FastHashMap<i64, String> {
    let mut tag_names = FastHashMap::default();

    for t in tags.chunks(1000) {
        let placeholders: Vec<String> = (1..=t.len()).map(|i| format!("${}", i)).collect();
        let query = format!(
            "SELECT t.id, t.name FROM tags t WHERE t.id IN ({});",
            placeholders.join(", ")
        );

        let params: Vec<&(dyn ToSql + Sync)> =
            t.iter().map(|id| id as &(dyn ToSql + Sync)).collect();

        let rows = db.query(&query, &params).await.unwrap();

        for row in rows {
            let id: i64 = row.get(0);
            let name: String = row.get(1);
            tag_names.insert(id, name);
        }
    }

    tag_names
}

pub async fn get_at_matrix(
    db: &Client,
    tag_indices: &FastHashMap<i64, usize>,
) -> (CsrMatrix<f64>, FastHashMap<i64, usize>) {
    let mut entries = Vec::new();
    for tags in tag_indices
        .keys()
        .cloned()
        .collect::<Vec<i64>>()
        .chunks(1000)
    {
        let placeholders: Vec<String> = (1..=tags.len()).map(|i| format!("${}", i)).collect();
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
    let n_cols = tag_indices.len();
    let mut matrix = CooMatrix::zeros(n_rows, n_cols);
    let mut account_indices: FastHashMap<i64, usize> = FastHashMap::default();

    for (account_id, tag_id, value) in entries.into_iter() {
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
    account_indices: &FastHashMap<i64, usize>,
) -> (CsrMatrix<f64>, FastHashMap<i64, usize>) {
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
    let mut tag_indices: FastHashMap<i64, usize> = FastHashMap::default();

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
    account_indices: &FastHashMap<i64, usize>,
) -> (CsrMatrix<f64>, FastHashMap<i64, usize>) {
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
    let mut producer_indices: FastHashMap<i64, usize> = FastHashMap::default();

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
    producer_indices: &FastHashMap<i64, usize>,
    tag_indices: &FastHashMap<i64, usize>,
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

pub async fn get_initial_engagements(db: &Client) -> impl Iterator<Item = (StatusEvent, EngagementEvent)> {
    let query = r#"
    SELECT
        e.status_id, 
        e.account_id,
        e.author_id,
        e.event_time,
        s.created_at,
        ARRAY_REMOVE(t.tags, NULL) as tags
    FROM enriched_status_engagement_events e
    join statuses s on s.id = e.status_id
    left join (
        select status_id, array_agg(tag_id) as tags from statuses_tags t
        group by status_id
    ) t on t.status_id = e.status_id
    WHERE e.event_time > NOW() - INTERVAL '60 DAYS'
    ORDER BY e.event_time;
    "#;

    let rows = db.query(query, &[]).await.unwrap();

    rows.into_iter().map(|row| {
        let status_id: i64 = row.get(0);
        let account_id: i64 = row.get(1);
        let author_id: i64 = row.get(2);
        let event_time: SystemTime = row.get(3);
        let created_at: SystemTime = row.get(4);
        let tags: Option<Vec<i64>> = row.get(5);
        let tags: FastHashSet<i64> = tags.unwrap_or_default().into_iter().collect();

        let status = StatusEvent {
            status_id,
            account_id: author_id,
            tags,
            created_at,
        };
        let engagement = EngagementEvent {
            account_id,
            status_id,
            author_id,
            event_time,
        };

        (status, engagement)
    })
}
