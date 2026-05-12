"""
Newsletter Email Template.
Used for periodic newsletter / bulletin-style communications.
"""

from app.modules.core.configs.config import settings


def newsletter_email_template(
    *,
    title: str,
    intro_text: str,
    sections: list[dict] | None = None,
    organization_name: str = "",
    sender_name: str = "",
    read_more_url: str = "",
    read_more_text: str = "Read More",
    support_email: str = "support@senat_digit.digipublic.app",
) -> str:
    """
    sections: list of {"heading": str, "body": str, "image_url"?: str}
    """
    LOGO_URL = f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/static/apps/senat_digit-app.png"
    safe_org = organization_name or "SenatDigit"
    safe_sender = sender_name or safe_org

    sections_html = ""
    for section in (sections or []):
        heading = section.get("heading", "")
        body = section.get("body", "")
        img = section.get("image_url", "")
        img_block = ""
        if img:
            img_block = f"""
                <tr><td style="padding:0 0 15px;">
                  <img src="{img}" width="100%" alt="" style="display:block;border:0;border-radius:8px;max-width:100%;">
                </td></tr>
            """
        sections_html += f"""
            <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                   style="background:#F7FBFF;border-radius:10px;border:1px solid #E0EBF5;margin-bottom:18px;">
              {img_block}
              <tr><td style="padding:20px;">
                <h3 style="margin:0 0 8px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:16px;color:#009EA1;">
                  {heading}
                </h3>
                <p style="margin:0;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;color:#2b2b2b;line-height:160%;">
                  {body}
                </p>
              </td></tr>
            </table>
        """

    cta_block = ""
    if read_more_url:
        cta_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin:25px 0;">
                  <tr><td align="center">
                    <a href="{read_more_url}"
                       style="display:inline-block;background-color:#009EA1;color:#ffffff;
                              font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;font-weight:700;
                              text-decoration:none;padding:14px 40px;border-radius:8px;">
                      {read_more_text}
                    </a>
                  </td></tr>
                </table>
        """

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{title}</title></head>
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

      <h1 style="margin:0 0 8px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:22px;color:#009EA1;">
        {title}
      </h1>

      <p style="margin:0 0 25px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;color:#2b2b2b;line-height:160%;">
        {intro_text}
      </p>

      {sections_html}

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
