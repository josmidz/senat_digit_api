"""
Feedback / Survey Email Template.
Used to request feedback, ratings, or survey participation from recipients.
"""

from app.modules.core.configs.config import settings


def feedback_survey_email_template(
    *,
    recipient_name: str = "",
    survey_title: str = "We Value Your Feedback",
    intro_text: str = "",
    show_rating_stars: bool = True,
    rating_url_base: str = "",
    survey_url: str = "",
    survey_button_text: str = "Take the Survey",
    questions_preview: list[str] | None = None,
    incentive_text: str = "",
    estimated_time: str = "",
    organization_name: str = "",
    sender_name: str = "",
    support_email: str = "support@senat_digit.digipublic.app",
) -> str:
    """
    Parameters
    ----------
    show_rating_stars : bool
        If True, render 1–5 star rating buttons using rating_url_base.
    rating_url_base : str
        Base URL for quick rating — will append ?rating=1..5
    questions_preview : list[str]
        Optional preview of survey questions displayed as a list.
    incentive_text : str
        Optional incentive message (e.g. "Complete the survey to win a gift card").
    """
    LOGO_URL = f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/static/apps/senat_digit-app.png"
    safe_recipient = recipient_name or "there"
    safe_org = organization_name or "SenatDigit"
    safe_sender = sender_name or safe_org
    safe_questions = questions_preview or []

    intro = intro_text or (
        f"Hello {safe_recipient}, we would love to hear about your experience. "
        "Your feedback helps us improve and serve you better."
    )

    # ── STAR RATING ──
    stars_block = ""
    if show_rating_stars and rating_url_base:
        star_cells = ""
        for i in range(1, 6):
            star_cells += f"""
                <td align="center" style="padding:0 6px;">
                  <a href="{rating_url_base}?rating={i}" style="text-decoration:none;">
                    <div style="width:48px;height:48px;line-height:48px;border-radius:50%;background:#F7FBFF;
                                border:2px solid #009EA1;font-size:22px;text-align:center;color:#009EA1;
                                font-weight:700;">{i}</div>
                    <div style="font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:10px;color:#888;margin-top:4px;">
                      {"&#9733;" * i}
                    </div>
                  </a>
                </td>
            """
        stars_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin:20px 0;">
                  <tr><td align="center">
                    <p style="margin:0 0 12px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;
                              color:#009EA1;font-weight:700;">
                      Quick Rating
                    </p>
                  </td></tr>
                  <tr><td align="center">
                    <table cellpadding="0" cellspacing="0" role="presentation">
                      <tr>{star_cells}</tr>
                    </table>
                  </td></tr>
                </table>
        """

    # ── QUESTIONS PREVIEW ──
    questions_block = ""
    if safe_questions:
        q_html = "".join(
            f"""<tr>
                  <td style="padding:10px 15px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;
                             color:#2b2b2b;border-bottom:1px solid #E0EBF5;">
                    <span style="color:#009EA1;font-weight:700;">Q{idx}.</span> {q}
                  </td>
                </tr>"""
            for idx, q in enumerate(safe_questions, 1)
        )
        questions_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                       style="background:#F7FBFF;border-radius:10px;border:1px solid #E0EBF5;margin:15px 0;">
                  <tr><td style="padding:12px 15px 4px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;
                                 color:#009EA1;font-weight:700;">
                    Here&rsquo;s a preview of what we&rsquo;ll ask:
                  </td></tr>
                  {q_html}
                  <tr><td style="padding:6px;"></td></tr>
                </table>
        """

    # ── INCENTIVE ──
    incentive_block = ""
    if incentive_text:
        incentive_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                       style="background:#ECFDF5;border-radius:10px;border:1px solid #A7F3D0;margin:15px 0;">
                  <tr><td style="padding:14px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;
                                 color:#065F46;line-height:150%;">
                    &#127873; <strong>{incentive_text}</strong>
                  </td></tr>
                </table>
        """

    time_block = ""
    if estimated_time:
        time_block = f"""
                <p style="margin:10px 0;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:12px;color:#888;text-align:center;">
                  &#9202; Estimated time: <strong>{estimated_time}</strong>
                </p>
        """

    survey_button_block = ""
    if survey_url:
        survey_button_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin:25px 0 10px;">
                  <tr><td align="center">
                    <a href="{survey_url}"
                       style="display:inline-block;background-color:#009EA1;color:#ffffff;
                              font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;font-weight:700;
                              text-decoration:none;padding:14px 40px;border-radius:8px;">
                      {survey_button_text}
                    </a>
                  </td></tr>
                </table>
        """

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Feedback</title></head>
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

      <h2 style="margin:0 0 14px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:20px;color:#009EA1;text-align:center;">
        {survey_title}
      </h2>

      <p style="margin:0 0 20px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;color:#2b2b2b;
                line-height:160%;text-align:center;">
        {intro}
      </p>

      {stars_block}
      {questions_block}
      {incentive_block}
      {time_block}
      {survey_button_block}

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
