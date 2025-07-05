from datetime import datetime

from sqlmodel import Field, SQLModel, Session


class CustomEmoji(SQLModel, table=True):
    __tablename__ = "custom_emojies"

    SHORTCODE_RE_FRAGMENT = r"[a-zA-Z0-9_]{2,}"
    SCAN_RE = re.compile(
        r"(?<=[^a-zA-Z0-9:]|\n|^)"
        r":(" + SHORTCODE_RE_FRAGMENT + r"):"
        r"(?=[^a-zA-Z0-9:]|$)",
        re.VERBOSE,
    )
    SHORTCODE_ONLY_RE = re.compile(r"^" + SHORTCODE_RE_FRAGMENT + r"$")
    IMAGE_MIME_TYPES = ["image/png", "image/gif", "image/webp"]

    id: int = Field(primary_key=True)
    shortcode: str = Field()
    domain: str | None = Field()

    created_at: datetime | None = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    @classmethod
    def from_text(
        cls, text: str, domain: str | None = None, db: Session = None
    ) -> list["CustomEmoji"]:
        if not text or not text.strip():
            return []

        # extract shortcodes from text
        matches = cls.SCAN_RE.findall(text)

        # drop duplicates
        shortcodes = list(set(matches))

        if not shortcodes:
            return []

        if db is None:
            raise ValueError("Session is required for database queries")

        query = select(cls).where(cls.shortcode.in_(shortcodes))

        if domain is not None:
            query = query.where(cls.domain == domain)
        else:
            query = query.where(cls.domain.is_(None))

        results = db.exec(query).all()

        return list(results)
