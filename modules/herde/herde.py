
from arango.database import StandardDatabase
from arango.graph import Graph

from modules.mastodon.models import (
    Status, StatusStats, Account, Tag, StatusTag, Mention, Follow, Favourite
)

class Herde():
    graph: Graph

    def __init__(self, graph: Graph):
        self.graph = graph

        self.accounts = graph.vertex_collection('accounts')
        self.statuses = graph.vertex_collection('statuses')
        self.tags = graph.vertex_collection('tags')

        self.follows = graph.edge("follows")
        self.tagged = graph.edge("tagged")
        self.favourited = graph.edge("favourited")
        self.reblogged = graph.edge("reblogged")
        self.replied = graph.edge("replied")
        self.created = graph.edge("created")

    def add_tag(self, tag: Tag):
        self.tags.insert({
            '_key': tag.id,
            'name': tag.name,
            'created_at': status.created_at if type(status.created_at) == int else int(status.created_at.timestamp() * 1000),
        }, overwrite=True)

    def add_status(self, statuse: Status):
        self.statuses.insert({
            '_key': status.id,
            'language': status.language,
            'created_at': status.created_at if type(status.created_at) == int else int(status.created_at.timestamp() * 1000),
        }, overwrite=True)

        self.created.insert({
            "_from": f"accounts/{status.account_id}",
            "_to": f"statuses/{status.id}",
        }, overwrite=True)

    def add_statuses(self, statuses: list[Status]):
        self.statuses.import_bulk([{
            '_key': status.id,
            'language': status.language,
            'created_at': status.created_at if type(status.created_at) == int else int(status.created_at.timestamp() * 1000),
        } for status in statuses])

        self.created.import_bulk([{
            "_from": f"accounts/{status.account_id}",
            "_to": f"statuses/{status.id}",
        } for status in statuses])
