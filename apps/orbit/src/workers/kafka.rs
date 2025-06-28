use std::time::Duration;

use rdkafka::{
    ClientConfig, ClientContext,
    admin::{AdminClient, AdminOptions, NewTopic, TopicReplication},
    client::DefaultClientContext,
    consumer::{Consumer, ConsumerContext, StreamConsumer},
    message::{BorrowedMessage, Message},
};
use tokio::{sync::mpsc::UnboundedSender, task::JoinHandle, time::sleep};

use crate::{
    config::Config,
    embedding::{EngagementEvent, StatusEvent},
};

const STATUSES_TOPIC: &str = "orbit_statuses";
const ENGAGEMENTS_TOPIC: &str = "orbit_engagements";
const TOPICS: [&str; 2] = [STATUSES_TOPIC, ENGAGEMENTS_TOPIC];

struct Context;

impl ClientContext for Context {}
impl ConsumerContext for Context {}

pub struct KafkaWorker {
    config: Config,
}

impl KafkaWorker {
    pub fn new(config: Config) -> Self {
        Self { config }
    }

    fn create_consumer(&self) -> StreamConsumer<Context> {
        ClientConfig::new()
            .set("group.id", &self.config.kafka_group_id)
            .set("bootstrap.servers", &self.config.kafka_bootstrap_servers)
            .set("enable.partition.eof", "false")
            .set("session.timeout.ms", "6000")
            .set("enable.auto.commit", "true")
            .set("auto.offset.reset", "latest")
            .set("allow.auto.create.topics", "true")
            .set("security.protocol", "PLAINTEXT")
            .create_with_context(Context)
            .unwrap()
    }

    pub fn start(self, event_tx: UnboundedSender<Event>) -> JoinHandle<()> {
        tracing::info!("Starting kafka worker");

        tokio::spawn(async move {
            if let Err(e) = self.run_consumer(event_tx).await {
                tracing::error!("Kafka worker failed: {}", e);
            }
        })
    }

    async fn run_consumer(
        &self,
        event_tx: UnboundedSender<Event>,
    ) -> Result<(), Box<dyn std::error::Error>> {
        // create kafka consumer
        let consumer = self.create_consumer();

        // wait for topics to be available before subscribing
        self.wait_for_topics(&consumer).await?;

        // subscribe to topics
        consumer.subscribe(&TOPICS).unwrap();
        tracing::info!("Kafka worker started, subscribed to topics: {:?}", TOPICS);

        // consume messages
        loop {
            match consumer.recv().await {
                Ok(message) => {
                    if let Err(e) = self.process_message(&message, &event_tx).await {
                        tracing::error!("Failed to process message: {}", e);
                    }
                }
                Err(e) => {
                    tracing::error!("Error receiving message: {}", e);
                    tokio::time::sleep(tokio::time::Duration::from_millis(1000)).await;
                }
            }
        }
    }

    async fn process_message(
        &self,
        message: &BorrowedMessage<'_>,
        event_tx: &UnboundedSender<Event>,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let topic = message.topic();
        let payload = match message.payload() {
            Some(payload) => payload,
            None => {
                tracing::warn!("Received message with no payload on topic: {}", topic);
                return Ok(());
            }
        };

        let payload_str = std::str::from_utf8(payload)?;

        // tracing::info!("Received message in {}: {}", topic, payload_str);

        match topic {
            STATUSES_TOPIC => match serde_json::from_str::<StatusEvent>(payload_str) {
                Ok(status_event) => {
                    if let Err(e) = event_tx.send(Event::Status(status_event)) {
                        tracing::error!("Failed to send status event: {}", e);
                    }
                }
                Err(e) => {
                    tracing::error!(
                        "Failed to deserialize status event: {}, payload: {}",
                        e,
                        payload_str
                    );
                }
            },
            ENGAGEMENTS_TOPIC => match serde_json::from_str::<EngagementEvent>(payload_str) {
                Ok(engagement_event) => {
                    if let Err(e) = event_tx.send(Event::Engagement(engagement_event)) {
                        tracing::error!("Failed to send engagement event: {}", e);
                    }
                }
                Err(e) => {
                    tracing::error!(
                        "Failed to deserialize engagement event: {}, payload: {}",
                        e,
                        payload_str
                    );
                }
            },
            _ => {
                tracing::warn!("Received message from unknown topic: {}", topic);
            }
        }

        Ok(())
    }

    async fn wait_for_topics(
        &self,
        consumer: &StreamConsumer<Context>,
    ) -> Result<(), Box<dyn std::error::Error>> {
        tracing::info!("Checking if topics exist: {:?}", TOPICS);

        // Create admin client to check/create topics
        let admin_client: AdminClient<DefaultClientContext> = ClientConfig::new()
            .set("bootstrap.servers", &self.config.kafka_bootstrap_servers)
            .create()?;

        // Get existing topics
        let metadata = consumer.fetch_metadata(None, Duration::from_secs(10))?;
        let existing_topics: std::collections::HashSet<String> = metadata
            .topics()
            .iter()
            .map(|t| t.name().to_string())
            .collect();

        // Check which topics need to be created
        let topics_to_create: Vec<&str> = TOPICS
            .iter()
            .cloned()
            .filter(|topic| !existing_topics.contains(*topic))
            .collect();

        if !topics_to_create.is_empty() {
            tracing::info!("Creating missing topics: {:?}", topics_to_create);

            let new_topics: Vec<NewTopic> = topics_to_create
                .iter()
                .map(|topic| NewTopic::new(topic, 1, TopicReplication::Fixed(1)))
                .collect();

            let opts = AdminOptions::new().operation_timeout(Some(Duration::from_secs(30)));

            match admin_client.create_topics(new_topics.iter(), &opts).await {
                Ok(results) => {
                    for result in results {
                        match result {
                            Ok(topic) => tracing::info!("Successfully created topic: {}", topic),
                            Err((topic, error)) => {
                                tracing::warn!("Failed to create topic {}: {}", topic, error)
                            }
                        }
                    }
                }
                Err(e) => {
                    tracing::warn!(
                        "Failed to create topics: {}. Topics may need to be created manually.",
                        e
                    );
                }
            }

            // Wait a bit for topics to be ready
            sleep(Duration::from_secs(2)).await;
        }

        Ok(())
    }
}

#[derive(Debug)]
pub enum Event {
    Status(StatusEvent),
    Engagement(EngagementEvent),
}
