# Import all models here so that Base has them before being
# imported by Alembic or used by create_all()
from app.db.base_class import Base # noqa
from app.db.models.user import User # noqa
from app.db.models.asset import Asset # noqa
from app.db.models.asset_frame import AssetFrame # noqa
from app.db.models.scan_job import ScanJob # noqa
from app.db.models.scraped_video import ScrapedVideo # noqa
from app.db.models.scraped_frame import ScrapedFrame # noqa
from app.db.models.detection_result import DetectionResult # noqa
from app.db.models.judge_review import JudgeReview # noqa
