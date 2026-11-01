"""
Consolidated registry import for all SQLAlchemy declarative models.
Ensures relationship mappers are always properly registered across all background services.
"""

from app.modules.users.models import User  # noqa: F401
from app.modules.telegram_accounts.models import TelegramAccount  # noqa: F401
from app.modules.telegram_chats.models import TelegramChat, TelegramMessage  # noqa: F401
from app.modules.url_scanning.models import ScannedUrl  # noqa: F401
from app.modules.threat_intelligence.models import ThreatIntelligence  # noqa: F401
from app.modules.risk_engine.models import ThreatAssessment  # noqa: F401
from app.modules.notifications.models import Notification  # noqa: F401
from app.modules.audit.models import AuditLog  # noqa: F401
