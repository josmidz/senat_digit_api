"""
Report / Summary Email Template.
Used for periodic reports — daily/weekly/monthly dashboards with metrics and key-value stats.
"""

from app.modules.core.configs.config import settings


def report_summary_email_template(
    *,
    recipient_name: str = "",
    report_title: str = "Your Report",
    report_period: str = "",
    metrics: list[dict] | None = None,
    highlights: list[str] | None = None,
    table_data: list[dict] | None = None,
    table_columns: list[str] | None = None,
    footer_note: str = "",
    action_url: str = "",
    action_button_text: str = "View Full Report",
    organization_name: str = "",
    sender_name: str = "",
    support_email: str = "support@senat_digit.digipublic.app",
) -> str:
    """
    Parameters
    ----------
    metrics : list[dict]
        Each dict: {"label": str, "value": str, "change": str (optional, e.g. "+12%")}
    highlights : list[str]
        Bullet-point highlights for the period.
    table_data : list[dict]
        Rows of key-value data. Keys must match table_columns.
    table_columns : list[str]
        Column headers for the data table.
    """
    LOGO_URL = f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/static/apps/senat_digit-app.png"
    safe_recipient = recipient_name or "there"
    safe_org = organization_name or "SenatDigit"
    safe_sender = sender_name or safe_org
    safe_metrics = metrics or []
    safe_highlights = highlights or []
    safe_table_data = table_data or []
    safe_table_columns = table_columns or []

    period_block = ""
    if report_period:
        period_block = f"""
                <p style="margin:0 0 10px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;
                          color:#888;text-align:center;">
                  Period: <strong style="color:#2b2b2b;">{report_period}</strong>
                </p>
        """

    # ── METRICS CARDS (up to 4 across) ──
    metrics_block = ""
    if safe_metrics:
        cells = ""
        card_width = max(25, 100 // max(len(safe_metrics), 1))
        for m in safe_metrics[:4]:
            change_html = ""
            change = m.get("change", "")
            if change:
                is_positive = change.strip().startswith("+")
                change_color = "#059669" if is_positive else "#DC2626"
                change_html = f"""
                    <div style="font-size:12px;color:{change_color};margin-top:4px;font-weight:700;">{change}</div>
                """
            cells += f"""
                <td width="{card_width}%" align="center" style="padding:8px;">
                  <div style="background:#F7FBFF;border:1px solid #E0EBF5;border-radius:10px;padding:16px 10px;">
                    <div style="font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:22px;font-weight:800;color:#009EA1;">
                      {m.get("value", "")}
                    </div>
                    <div style="font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:11px;color:#888;
                                text-transform:uppercase;letter-spacing:0.5px;margin-top:6px;">
                      {m.get("label", "")}
                    </div>
                    {change_html}
                  </div>
                </td>
            """
        metrics_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin:15px 0;">
                  <tr>{cells}</tr>
                </table>
        """

    # ── HIGHLIGHTS ──
    highlights_block = ""
    if safe_highlights:
        li_html = "".join(
            f'<li style="margin-bottom:6px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;color:#2b2b2b;line-height:150%;">{h}</li>'
            for h in safe_highlights
        )
        highlights_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                       style="background:#F7FBFF;border-radius:10px;border:1px solid #E0EBF5;margin:15px 0;">
                  <tr><td style="padding:14px 15px 4px;">
                    <strong style="font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;color:#009EA1;">
                      Key Highlights
                    </strong>
                  </td></tr>
                  <tr><td style="padding:6px 20px 14px;">
                    <ul style="margin:0;padding-left:18px;">{li_html}</ul>
                  </td></tr>
                </table>
        """

    # ── DATA TABLE ──
    data_table_block = ""
    if safe_table_columns and safe_table_data:
        header_cells = "".join(
            f"""<td style="padding:10px 12px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:11px;
                           color:#009EA1;text-transform:uppercase;letter-spacing:0.5px;font-weight:700;
                           border-bottom:2px solid #009EA1;">{col}</td>"""
            for col in safe_table_columns
        )
        data_rows = ""
        for row in safe_table_data:
            row_cells = "".join(
                f"""<td style="padding:8px 12px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;
                               color:#2b2b2b;border-bottom:1px solid #E0EBF5;">{row.get(col, "")}</td>"""
                for col in safe_table_columns
            )
            data_rows += f"<tr>{row_cells}</tr>"

        data_table_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                       style="border:1px solid #E0EBF5;border-radius:10px;margin:15px 0;overflow:hidden;">
                  <tr>{header_cells}</tr>
                  {data_rows}
                </table>
        """

    footer_note_block = ""
    if footer_note:
        footer_note_block = f"""
                <p style="margin:10px 0;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:12px;color:#888;
                          font-style:italic;">
                  {footer_note}
                </p>
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
<head><meta charset="utf-8"><title>Report</title></head>
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

      <h2 style="margin:0 0 6px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:20px;color:#009EA1;text-align:center;">
        {report_title}
      </h2>
      {period_block}

      <p style="margin:0 0 20px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;color:#2b2b2b;
                line-height:160%;">
        Hello {safe_recipient}, here is a summary of your latest report.
      </p>

      {metrics_block}
      {highlights_block}
      {data_table_block}
      {footer_note_block}
      {action_block}

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
