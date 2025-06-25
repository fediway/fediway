
use tokio_postgres::{Client, types::ToSql};
use std::collections::HashMap;

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
    JOIN tag_features tf1 ON tf1.tag_id = e1.tag_id
    JOIN tag_features tf2 ON tf2.tag_id = e2.tag_id
    WHERE e1.tag_id < e2.tag_id
    GROUP BY e1.tag_id, e2.tag_id
    HAVING COUNT(distinct e1.account_id) >= 15;
    "#;

    db.query(query, &[])
        .await
        .unwrap()
        .into_iter()
        .map(|row| {
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

    let params: Vec<&(dyn ToSql + Sync)> = tags
        .iter()
        .map(|id| id as &(dyn ToSql + Sync))
        .collect();

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