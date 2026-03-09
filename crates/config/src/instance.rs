use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct InstanceConfig {
    pub instance_domain: String,
    pub instance_name: String,
}
