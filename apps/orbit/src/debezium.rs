use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct DebeziumEvent<T> {
    pub schema: Option<Schema>,
    pub payload: Option<Payload<T>>,
}

impl<T> DebeziumEvent<T> {
    pub fn new_create(event: T) -> Self {
        Self {
            schema: None,
            payload: Some(Payload {
                before: None,
                after: Some(event),
                source: Source::default(),
                op: Operation::Create,
                timestamp_ms: None,
                transaction: None,
            }),
        }
    }
}

#[derive(Debug, Deserialize)]
pub struct Schema {
    #[serde(rename = "type")]
    pub schema_type: String,
    pub fields: Option<Vec<Field>>,
    pub optional: Option<bool>,
    pub name: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct Field {
    #[serde(rename = "type")]
    pub field_type: String,
    pub fields: Option<Vec<Field>>,
    pub optional: Option<bool>,
    pub name: Option<String>,
    pub field: Option<String>,
}

#[derive(Debug, Deserialize)]
pub enum Operation {
    #[serde(rename = "c")]
    Create,
    #[serde(rename = "u")]
    Update,
    #[serde(rename = "d")]
    Delete,
    #[serde(rename = "r")]
    Read,
}

#[derive(Debug, Deserialize)]
pub struct Payload<T> {
    pub before: Option<T>,
    pub after: Option<T>,
    pub source: Source,
    pub op: Operation,
    #[serde(rename = "ts_ms")]
    pub timestamp_ms: Option<i64>,
    pub transaction: Option<Transaction>,
}

#[derive(Debug, Deserialize, Default)]
pub struct Source {
    #[serde(rename = "ts_ms")]
    pub timestamp_ms: i64,
    pub db: Option<String>,
    pub table: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct Transaction {
    pub id: String,
    #[serde(rename = "total_order")]
    pub total_order: i64,
    #[serde(rename = "data_collection_order")]
    pub data_collection_order: i64,
}
