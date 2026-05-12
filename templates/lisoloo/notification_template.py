"""
Notification / Alert Email Template.
General-purpose notification for system alerts, status updates, reminders, etc.
"""

from app.modules.core.configs.config import settings


def notification_email_template(
    *,
    recipient_name: str = "",
    notification_title: str,
    notification_body: str,
    severity: str = "info",
    action_button_url: str = "",
    action_button_text: str = "View Details",
    organization_name: str = "",
    sender_name: str = "",
    support_email: str = "support@senat_digit.digipublic.app",
) -> str:
    """
    severity: 'info' | 'warning' | 'error' | 'success'
    """
    LOGO_URL = f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/static/apps/senat_digit-app.png"
    safe_recipient = recipient_name or "there"
    safe_org = organization_name or "SenatDigit"
    safe_sender = sender_name or safe_org

    # Severity colour mapping
    colour_map = {
        "info":    {"bg": "#EFF6FF", "border": "#BFDBFE", "accent": "#2563EB", "icon": "ℹ️"},
        "warning": {"bg": "#FFFBEB", "border": "#FDE68A", "accent": "#D97706", "icon": "⚠️"},
        "error":   {"bg": "#FEF2F2", "border": "#FECACA", "accent": "#DC2626", "icon": "🚨"},
        "success": {"bg": "#F0FDF4", "border": "#BBF7D0", "accent": "#16A34A", "icon": "✅"},
    }
    c = colour_map.get(severity, colour_map["info"])

    cta_block = ""
    if action_button_url:
        cta_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin:28px 0;">
                  <tr><td align="center">
                    <a href="{action_button_url}"
                       style="display:inline-block;background-color:{c['accent']};color:#ffffff;
                              font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;font-weight:700;
                              text-decoration:none;padding:14px 40px;border-radius:8px;">
                      {action_button_text}
                    </a>
                  </td></tr>
                </table>
        """

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{notification_title}</title></head>
<body style="margin:0;padding:0;background-color:#F0F8FF;">
<table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background-color:#F0F8FF;">
<tr><td align="center" style="padding:20px 10px;">

  <!-- LOGO -->
  <table width="700" cellpadding="0" cellspacing="0" role="presentation" style="background:#ffffff;border-radius:10px;">
    <tr><td align="center" style="padding:25px;">
      <img src="{LOGO_URL}" width="120" alt="SenatDigit" style="display:block;border:0;">
    </td></tr>
  </table>

  <!-- CONTENT -->
  <table width="700" cellpadding="0" cellspacing="0" role="presentation"
         style="background:#ffffff;border-radius:10px;margin-top:15px;">
    <tr><td style="padding:40px 50px;">

      <p style="margin:0 0 20px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;color:#2b2b2b;">
        Hello {safe_recipient},
      </p>

      <!-- NOTIFICATION BOX -->
      <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
             style="background:{c['bg']};border-radius:10px;border:1px solid {c['border']};margin:10px 0 25px;">
        <tr><td style="padding:25px;">
          <h2 style="margin:0 0 12px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:18px;color:{c['accent']};">
            {c['icon']} {notification_title}
          </h2>
          <p style="margin:0;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;color:#2b2b2b;line-height:160%;">
            {notification_body}
          </p>
        </td></tr>
      </table>

      {cta_block}

      <hr style="border:0;border-top:1px solid #E0EBF5;margin:25px 0;">

      <p style="margin:0;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;color:#009EA1;">
        Best regards,
      </p>
      <p style="margin:4px 0 0;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;color:#1d2144;">
        <strong>{safe_sender}</strong>
      </p>

    </td></tr>
  </table>

  <!-- FOOTER -->
  <table width="700" cellpadding="0" cellspacing="0" role="presentation"
         style="background:#1E293B;border-radius:10px;margin-top:15px;">
    <tr><td style="padding:20px 40px;">
      <p style="margin:0;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:12px;color:#CBD5E1;">
        Support: <a href="mailto:{support_email}" style="color:#38BDF8;text-decoration:none;font-weight:700;">{support_email}</a>
      </p>
      <p style="margin:8px 0 0;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:12px;color:#CBD5E1;">
        This is an automated message. Please do not reply.
      </p>
      <p style="margin:6px 0 0;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:12px;color:#CBD5E1;">
        &copy; {safe_org}. All rights reserved.
      </p>
    </td></tr>
  </table>

</td></tr>
</table>
</body>
</html>
"""
