"""
Lisoloo Email Templates.

10 ready-to-use HTML email templates for the SenatDigit Lisoloo email system.
Each function returns a complete HTML string; all use keyword-only arguments.
"""

from .welcome_template import welcome_email_template
from .newsletter_template import newsletter_email_template
from .notification_template import notification_email_template
from .promotional_template import promotional_email_template
from .invoice_template import invoice_email_template
from .password_reset_template import password_reset_email_template
from .event_invitation_template import event_invitation_email_template
from .confirmation_receipt_template import confirmation_receipt_email_template
from .report_summary_template import report_summary_email_template
from .feedback_survey_template import feedback_survey_email_template
from .general_template import general_email_template

__all__ = [
    "welcome_email_template",
    "newsletter_email_template",
    "notification_email_template",
    "promotional_email_template",
    "invoice_email_template",
    "password_reset_email_template",
    "event_invitation_email_template",
    "confirmation_receipt_email_template",
    "report_summary_email_template",
    "feedback_survey_email_template",
    "general_email_template",
]
