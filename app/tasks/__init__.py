
import faust
from app.config import settings

app = faust.App(
    'myapp',
    broker=settings.kafka_broker_url,
    autodiscover=True,
    origin='app.tasks',  # Tell Faust where to look for agents/crons
)