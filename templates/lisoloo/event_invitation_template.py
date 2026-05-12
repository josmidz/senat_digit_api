"""
Event Invitation Email Template.
Used for sending event invitations with details like date, time, location, and RSVP.
"""

from app.modules.core.configs.config import settings


def event_invitation_email_template(
    *,
    recipient_name: str = "",
    event_name: str,
    event_date: str,
    event_time: str = "",
    event_location: str = "",
    event_description: str = "",
    event_image_url: str = "",
    rsvp_url: str = "",
    rsvp_button_text: str = "RSVP Now",
    organizer_name: str = "",
    organization_name: str = "",
    sender_name: str = "",
    support_email: str = "support@senat_digit.digipublic.app",
) -> str:
    LOGO_URL = f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/static/apps/senat_digit-app.png"
    safe_recipient = recipient_name or "there"
    safe_org = organization_name or "SenatDigit"
    safe_sender = sender_name or safe_org

    hero_block = ""
    if event_image_url:
        hero_block = f"""
                <tr><td style="padding:0;">
                  <img src="{event_image_url}" alt="{event_name}"
                       style="display:block;width:100%;max-height:300px;object-fit:cover;border-radius:10px 10px 0 0;">
                </td></tr>
        """

    description_block = ""
    if event_description:
        description_block = f"""
                <p style="margin:0 0 20px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;
                          color:#2b2b2b;line-height:160%;">
                  {event_description}
                </p>
        """

    def _detail_row(icon: str, label: str, value: str) -> str:
        return f"""
                <tr>
                  <td style="padding:10px 15px;width:30px;vertical-align:top;font-size:18px;">{icon}</td>
                  <td style="padding:10px 15px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;">
                    <div style="font-size:11px;color:#009EA1;text-transform:uppercase;letter-spacing:0.5px;font-weight:700;">{label}</div>
                    <div style="font-size:14px;color:#2b2b2b;margin-top:3px;">{value}</div>
                  </td>
                </tr>
        """

    details_rows = _detail_row("&#128197;", "Date", event_date)
    if event_time:
        details_rows += _detail_row("&#128336;", "Time", event_time)
    if event_location:
        details_rows += _detail_row("&#128205;", "Location", event_location)
    if organizer_name:
        details_rows += _detail_row("&#128100;", "Organizer", organizer_name)

    rsvp_block = ""
    if rsvp_url:
        rsvp_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin:25px 0 10px;">
                  <tr><td align="center">
                    <a href="{rsvp_url}"
                       style="display:inline-block;background-color:#009EA1;color:#ffffff;
                              font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;font-weight:700;
                              text-decoration:none;padding:14px 40px;border-radius:8px;">
                      {rsvp_button_text}
                    </a>
                  </td></tr>
                </table>
        """

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Event Invitation</title></head>
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
    {hero_block}
    <tr><td style="padding:40px 50px;">

      <p style="margin:0 0 6px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:12px;
                color:#009EA1;text-transform:uppercase;letter-spacing:1px;font-weight:700;">
        You&rsquo;re Invited
      </p>

      <h2 style="margin:0 0 16px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:22px;color:#1d2144;">
        {event_name}
      </h2>

      <p style="margin:0 0 18px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;color:#2b2b2b;line-height:160%;">
        Hello {safe_recipient}, you are cordially invited to the following event. We would love to see you there!
      </p>

      {description_block}

      <!-- EVENT DETAILS -->
      <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
             style="background:#F7FBFF;border-radius:10px;border:1px solid #E0EBF5;margin:10px 0;">
        {details_rows}
      </table>

      {rsvp_block}

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
