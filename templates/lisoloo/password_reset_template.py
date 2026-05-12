"""
Password Reset / Account Security Email Template.
Sent when a user requests a password reset, or for other account-security actions.
"""

from app.modules.core.configs.config import settings


def password_reset_email_template(
    *,
    recipient_name: str = "",
    reset_url: str,
    reset_code: str = "",
    expiry_minutes: int = 30,
    ip_address: str = "",
    device_info: str = "",
    organization_name: str = "",
    sender_name: str = "",
    support_email: str = "support@senat_digit.digipublic.app",
) -> str:
    LOGO_URL = f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/static/apps/senat_digit-app.png"
    safe_recipient = recipient_name or "there"
    safe_org = organization_name or "SenatDigit"
    safe_sender = sender_name or safe_org

    code_block = ""
    if reset_code:
        code_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                       style="background:#009EA1;border-radius:10px;margin:25px 0;">
                  <tr><td align="center" style="padding:22px;">
                    <div style="font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:12px;
                                color:#E0FFFF;letter-spacing:1px;text-transform:uppercase;">
                      Reset Code
                    </div>
                    <div style="font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:34px;
                                font-weight:800;letter-spacing:8px;color:#ffffff;margin:8px 0;">
                      {reset_code}
                    </div>
                    <div style="font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:12px;color:#E0FFFF;">
                      Valid for {expiry_minutes} minutes
                    </div>
                  </td></tr>
                </table>
        """

    context_rows = ""
    if ip_address:
        context_rows += f"""
                <tr><td style="padding:6px 15px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;border-top:1px solid #E0EBF5;">
                  <strong style="color:#009EA1;">IP Address:</strong> <span style="color:#2b2b2b;">{ip_address}</span>
                </td></tr>
        """
    if device_info:
        context_rows += f"""
                <tr><td style="padding:6px 15px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;border-top:1px solid #E0EBF5;">
                  <strong style="color:#009EA1;">Device:</strong> <span style="color:#2b2b2b;">{device_info}</span>
                </td></tr>
        """

    context_block = ""
    if context_rows:
        context_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                       style="background:#F7FBFF;border-radius:10px;border:1px solid #E0EBF5;margin:15px 0;">
                  <tr><td style="padding:12px 15px 4px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;font-weight:700;color:#009EA1;">
                    Request Info
                  </td></tr>
                  {context_rows}
                  <tr><td style="padding:6px;"></td></tr>
                </table>
        """

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Password Reset</title></head>
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

      <h2 style="margin:0 0 10px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:20px;color:#009EA1;">
        Password Reset Request
      </h2>

      <p style="margin:0 0 20px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;color:#2b2b2b;line-height:160%;">
        Hello {safe_recipient}, we received a request to reset your password. Click the button below or use the code to proceed.
      </p>

      {code_block}

      <!-- RESET BUTTON -->
      <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin:25px 0;">
        <tr><td align="center">
          <a href="{reset_url}"
             style="display:inline-block;background-color:#009EA1;color:#ffffff;
                    font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;font-weight:700;
                    text-decoration:none;padding:14px 40px;border-radius:8px;">
            Reset My Password
          </a>
        </td></tr>
      </table>

      {context_block}

      <!-- SECURITY NOTICE -->
      <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
             style="background:#FEF2F2;border-radius:10px;border:1px solid #FECACA;margin-top:18px;">
        <tr><td style="padding:14px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;color:#991B1B;line-height:150%;">
          <strong style="color:#DC2626;">Security Notice:</strong>
          <ul style="margin:10px 0 0 18px;padding:0;">
            <li>This link expires in {expiry_minutes} minutes</li>
            <li>If you did not request this, please ignore this email</li>
            <li>Never share your reset code with anyone</li>
          </ul>
        </td></tr>
      </table>

      <hr style="border:0;border-top:1px solid #E0EBF5;margin:25px 0;">

      <p style="margin:0;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;color:#009EA1;">Best regards,</p>
      <p style="margin:4px 0 0;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;color:#1d2144;"><strong>{safe_sender}</strong></p>

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
