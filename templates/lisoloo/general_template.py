"""
General-Purpose Email Template.
A versatile, clean template for any type of email that does not fit a
specific category. Supports a title, body HTML, optional CTA button,
and optional footer note.
"""

from app.modules.core.configs.config import settings


def general_email_template(
    *,
    recipient_name: str = "",
    email_title: str,
    email_body: str,
    action_button_url: str = "",
    action_button_text: str = "Learn More",
    footer_note: str = "",
    organization_name: str = "",
    sender_name: str = "",
    support_email: str = "support@senat_digit.digipublic.app",
) -> str:
    LOGO_URL = f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/static/apps/senat_digit-app.png"
    safe_recipient = recipient_name or "there"
    safe_org = organization_name or "SenatDigit"
    safe_sender = sender_name or safe_org

    cta_block = ""
    if action_button_url:
        cta_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin:30px 0;">
                  <tr>
                    <td align="center">
                      <a href="{action_button_url}"
                         style="display:inline-block;padding:14px 36px;background-color:#009EA1;color:#ffffff;
                                text-decoration:none;border-radius:8px;font-weight:600;font-size:16px;"
                         target="_blank">{action_button_text}</a>
                    </td>
                  </tr>
                </table>"""

    footer_note_block = ""
    if footer_note:
        footer_note_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin-top:20px;">
                  <tr>
                    <td style="padding:16px 20px;background-color:#F0F8FF;border-radius:8px;
                               font-size:13px;color:#64748B;line-height:1.6;">
                      {footer_note}
                    </td>
                  </tr>
                </table>"""

    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <title>{email_title}</title>
</head>
<body style="margin:0;padding:0;background-color:#F0F8FF;font-family:'Roboto',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background-color:#F0F8FF;">
    <tr>
      <td align="center" style="padding:30px 15px;">
        <table width="700" cellpadding="0" cellspacing="0" role="presentation"
               style="max-width:700px;width:100%;background-color:#ffffff;border-radius:12px;
                      box-shadow:0 4px 24px rgba(0,0,0,0.06);overflow:hidden;">
          <!-- HEADER -->
          <tr>
            <td style="background:linear-gradient(135deg,#009EA1 0%,#007B7E 100%);padding:35px 40px;text-align:center;">
              <img src="{LOGO_URL}" alt="{safe_org}" width="48" height="48"
                   style="display:block;margin:0 auto 14px;" />
              <h1 style="margin:0;font-size:24px;font-weight:700;color:#ffffff;line-height:1.3;">
                {email_title}
              </h1>
            </td>
          </tr>

          <!-- BODY -->
          <tr>
            <td style="padding:40px;">
              <p style="margin:0 0 20px;font-size:16px;color:#334155;line-height:1.6;">
                Hello {safe_recipient},
              </p>
              <div style="font-size:15px;color:#475569;line-height:1.7;">
                {email_body}
              </div>
              {cta_block}
              {footer_note_block}
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="background-color:#1E293B;padding:30px 40px;text-align:center;">
              <p style="margin:0 0 6px;font-size:13px;color:#94A3B8;line-height:1.5;">
                Sent by {safe_sender}
              </p>
              <p style="margin:0;font-size:12px;color:#64748B;line-height:1.5;">
                Questions? Contact us at
                <a href="mailto:{support_email}" style="color:#009EA1;text-decoration:none;">{support_email}</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
