"""
Promotional / Marketing Email Template.
Used for product announcements, sales, special offers, etc.
"""

from app.modules.core.configs.config import settings


def promotional_email_template(
    *,
    headline: str,
    sub_headline: str = "",
    body_text: str,
    promo_code: str = "",
    promo_expiry: str = "",
    hero_image_url: str = "",
    cta_url: str = "",
    cta_text: str = "Shop Now",
    organization_name: str = "",
    sender_name: str = "",
    support_email: str = "support@senat_digit.digipublic.app",
) -> str:
    LOGO_URL = f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/static/apps/senat_digit-app.png"
    safe_org = organization_name or "SenatDigit"
    safe_sender = sender_name or safe_org

    hero_block = ""
    if hero_image_url:
        hero_block = f"""
      <table width="700" cellpadding="0" cellspacing="0" role="presentation"
             style="border-radius:10px;overflow:hidden;margin-top:15px;">
        <tr><td>
          <img src="{hero_image_url}" width="700" alt="" style="display:block;border:0;width:100%;border-radius:10px;">
        </td></tr>
      </table>
        """

    promo_block = ""
    if promo_code:
        expiry_line = f'<div style="font-size:12px;color:#6B7280;margin-top:6px;">Expires: {promo_expiry}</div>' if promo_expiry else ""
        promo_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                       style="background:#009EA1;border-radius:10px;margin:25px 0;">
                  <tr><td align="center" style="padding:22px;">
                    <div style="font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:12px;
                                color:#E0FFFF;letter-spacing:1px;text-transform:uppercase;">
                      Your Promo Code
                    </div>
                    <div style="font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:28px;
                                font-weight:800;letter-spacing:6px;color:#ffffff;margin:8px 0;">
                      {promo_code}
                    </div>
                    {expiry_line}
                  </td></tr>
                </table>
        """

    cta_block = ""
    if cta_url:
        cta_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin:28px 0;">
                  <tr><td align="center">
                    <a href="{cta_url}"
                       style="display:inline-block;background-color:#009EA1;color:#ffffff;
                              font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:15px;font-weight:700;
                              text-decoration:none;padding:16px 50px;border-radius:8px;">
                      {cta_text}
                    </a>
                  </td></tr>
                </table>
        """

    sub_head = ""
    if sub_headline:
        sub_head = f"""
      <p style="margin:0 0 20px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:15px;color:#64748B;line-height:150%;">
        {sub_headline}
      </p>
        """

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{headline}</title></head>
<body style="margin:0;padding:0;background-color:#F0F8FF;">
<table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background-color:#F0F8FF;">
<tr><td align="center" style="padding:20px 10px;">

  <!-- LOGO -->
  <table width="700" cellpadding="0" cellspacing="0" role="presentation" style="background:#ffffff;border-radius:10px;">
    <tr><td align="center" style="padding:25px;">
      <img src="{LOGO_URL}" width="120" alt="SenatDigit" style="display:block;border:0;">
    </td></tr>
  </table>

  {hero_block}

  <!-- CONTENT -->
  <table width="700" cellpadding="0" cellspacing="0" role="presentation"
         style="background:#ffffff;border-radius:10px;margin-top:15px;">
    <tr><td style="padding:40px 50px;">

      <h1 style="margin:0 0 10px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:24px;color:#009EA1;text-align:center;">
        {headline}
      </h1>

      {sub_head}

      <p style="margin:0 0 20px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;color:#2b2b2b;line-height:160%;">
        {body_text}
      </p>

      {promo_block}

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
