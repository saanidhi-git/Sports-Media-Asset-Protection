# Import all models here so that Base has them before being
# imported by Alembic or used by create_all()
from app.db.base_class import Base # noqa
from app.db.models.user import User # noqa
from app.db.models.asset import Asset # noqa
