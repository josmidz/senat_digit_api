"""
Confirmation / Receipt Email Template.
Sent after a user completes an action — e.g. order confirmation, booking, registration.
"""

from app.modules.core.configs.config import settings


def confirmation_receipt_email_template(
    *,
    recipient_name: str = "",
    confirmation_title: str = "Your Action Is Confirmed",
    confirmation_number: str = "",
    summary_items: list[dict] | None = None,
    total_amount: str = "",
    currency: str = "",
    confirmation_date: str = "",
    additional_note: str = "",
    action_url: str = "",
    action_button_text: str = "View Details",
    organization_name: str = "",
    sender_name: str = "",
    support_email: str = "support@senat_digit.digipublic.app",
) -> str:
    LOGO_URL = f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/static/apps/senat_digit-app.png"
    safe_recipient = recipient_name or "there"
    safe_org = organization_name or "SenatDigit"
    safe_sender = sender_name or safe_org
    safe_items = summary_items or []

    conf_num_block = ""
    if confirmation_number:
        conf_num_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                       style="background:#009EA1;border-radius:10px;margin:20px 0;">
                  <tr><td align="center" style="padding:18px;">
                    <div style="font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:11px;
                                color:#E0FFFF;letter-spacing:1px;text-transform:uppercase;">
                      Confirmation Number
                    </div>
                    <div style="font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:24px;
                                font-weight:800;letter-spacing:4px;color:#ffffff;margin-top:6px;">
                      {confirmation_number}
                    </div>
                  </td></tr>
                </table>
        """

    items_block = ""
    if safe_items:
        rows_html = ""
        for item in safe_items:
            label = item.get("label", "")
            value = item.get("value", "")
            rows_html += f"""
                  <tr>
                    <td style="padding:10px 15px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;
                               color:#555;border-bottom:1px solid #E0EBF5;">
                      {label}
                    </td>
                    <td style="padding:10px 15px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;
                               color:#2b2b2b;font-weight:700;text-align:right;border-bottom:1px solid #E0EBF5;">
                      {value}
                    </td>
                  </tr>
            """

        total_row = ""
        if total_amount:
            currency_str = f"{currency} " if currency else ""
            total_row = f"""
                  <tr>
                    <td style="padding:12px 15px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;
                               color:#009EA1;font-weight:700;">
                      Total
                    </td>
                    <td style="padding:12px 15px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:16px;
                               color:#009EA1;font-weight:800;text-align:right;">
                      {currency_str}{total_amount}
                    </td>
                  </tr>
            """

        items_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                       style="background:#F7FBFF;border-radius:10px;border:1px solid #E0EBF5;margin:15px 0;">
                  <tr>
                    <td style="padding:10px 15px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:11px;
                               color:#009EA1;text-transform:uppercase;letter-spacing:0.5px;font-weight:700;border-bottom:2px solid #009EA1;">
                      Item
                    </td>
                    <td style="padding:10px 15px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:11px;
                               color:#009EA1;text-transform:uppercase;letter-spacing:0.5px;font-weight:700;text-align:right;border-bottom:2px solid #009EA1;">
                      Details
                    </td>
                  </tr>
                  {rows_html}
                  {total_row}
                </table>
        """

    date_block = ""
    if confirmation_date:
        date_block = f"""
                <p style="margin:10px 0;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;color:#888;">
                  Date: <strong style="color:#2b2b2b;">{confirmation_date}</strong>
                </p>
        """

    note_block = ""
    if additional_note:
        note_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                       style="background:#FFFBEB;border-radius:10px;border:1px solid #FDE68A;margin:15px 0;">
                  <tr><td style="padding:14px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;
                                 color:#92400E;line-height:150%;">
                    <strong>Note:</strong> {additional_note}
                  </td></tr>
                </table>
        """

    action_block = ""
    if action_url:
        action_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin:25px 0 10px;">
                  <tr><td align="center">
                    <a href="{action_url}"
                       style="display:inline-block;background-color:#009EA1;color:#ffffff;
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
<head><meta charset="utf-8"><title>Confirmation</title></head>
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

      <!-- SUCCESS ICON -->
      <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin-bottom:20px;">
        <tr><td align="center">
          <div style="width:60px;height:60px;border-radius:50%;background:#ECFDF5;line-height:60px;text-align:center;font-size:28px;">
            &#10003;
          </div>
        </td></tr>
      </table>

      <h2 style="margin:0 0 10px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:20px;color:#009EA1;text-align:center;">
        {confirmation_title}
      </h2>

      <p style="margin:0 0 18px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;color:#2b2b2b;
                line-height:160%;text-align:center;">
        Hello {safe_recipient}, your request has been processed successfully.
      </p>

      {conf_num_block}
      {date_block}
      {items_block}
      {note_block}
      {action_block}

      <hr style="border:0;border-top:1px solid #E0EBF5;margin:25px 0;">

      <p style="margin:0;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;color:#009EA1;">Thank you,</p>
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
