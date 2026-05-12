"""
Invoice / Payment Email Template.
Sent when an invoice is created, a payment is due, or a payment is confirmed.
"""

from app.modules.core.configs.config import settings


def _detail_row(label: str, value: str) -> str:
    return f"""
    <tr>
      <td style="padding:8px 15px;
                 font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;
                 font-size:13px;
                 border-top:1px solid #E0EBF5;">
        <strong style="color:#009EA1;">{label}:</strong>
        <span style="color:#2b2b2b;"> {value}</span>
      </td>
    </tr>
    """


def invoice_email_template(
    *,
    recipient_name: str = "",
    invoice_number: str,
    amount: float,
    currency: str = "USD",
    due_date: str = "",
    status: str = "pending",
    items: list[dict] | None = None,
    payment_url: str = "",
    payment_button_text: str = "Pay Now",
    organization_name: str = "",
    sender_name: str = "",
    support_email: str = "support@senat_digit.digipublic.app",
) -> str:
    """
    status: 'pending' | 'paid' | 'overdue'
    items: list of {"description": str, "quantity": int, "unit_price": float}
    """
    LOGO_URL = f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/static/apps/senat_digit-app.png"
    safe_recipient = recipient_name or "Customer"
    safe_org = organization_name or "SenatDigit"
    safe_sender = sender_name or safe_org

    status_map = {
        "pending":  {"color": "#D97706", "bg": "#FFFBEB", "label": "Payment Pending"},
        "paid":     {"color": "#16A34A", "bg": "#F0FDF4", "label": "Paid"},
        "overdue":  {"color": "#DC2626", "bg": "#FEF2F2", "label": "Overdue"},
    }
    s = status_map.get(status, status_map["pending"])

    # Build items table
    items_html = ""
    if items:
        rows = ""
        for it in items:
            desc = it.get("description", "")
            qty = it.get("quantity", 1)
            price = it.get("unit_price", 0)
            line_total = qty * price
            rows += f"""
                <tr>
                  <td style="padding:8px 12px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;color:#2b2b2b;border-top:1px solid #E0EBF5;">{desc}</td>
                  <td style="padding:8px 12px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;color:#2b2b2b;border-top:1px solid #E0EBF5;text-align:center;">{qty}</td>
                  <td style="padding:8px 12px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;color:#2b2b2b;border-top:1px solid #E0EBF5;text-align:right;">{currency} {price:,.2f}</td>
                  <td style="padding:8px 12px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:13px;color:#2b2b2b;border-top:1px solid #E0EBF5;text-align:right;">{currency} {line_total:,.2f}</td>
                </tr>
            """
        items_html = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                       style="border-radius:10px;border:1px solid #E0EBF5;margin:20px 0;">
                  <tr>
                    <td style="padding:10px 12px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:12px;font-weight:700;color:#009EA1;background:#F7FBFF;">Description</td>
                    <td style="padding:10px 12px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:12px;font-weight:700;color:#009EA1;background:#F7FBFF;text-align:center;">Qty</td>
                    <td style="padding:10px 12px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:12px;font-weight:700;color:#009EA1;background:#F7FBFF;text-align:right;">Unit Price</td>
                    <td style="padding:10px 12px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:12px;font-weight:700;color:#009EA1;background:#F7FBFF;text-align:right;">Total</td>
                  </tr>
                  {rows}
                  <tr>
                    <td colspan="3" style="padding:10px 12px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;font-weight:700;color:#1d2144;text-align:right;border-top:2px solid #009EA1;">
                      Total
                    </td>
                    <td style="padding:10px 12px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;font-weight:700;color:#1d2144;text-align:right;border-top:2px solid #009EA1;">
                      {currency} {amount:,.2f}
                    </td>
                  </tr>
                </table>
        """

    # Summary details
    details = _detail_row("Invoice #", invoice_number)
    details += _detail_row("Amount Due", f"{currency} {amount:,.2f}")
    if due_date:
        details += _detail_row("Due Date", due_date)

    cta_block = ""
    if payment_url and status != "paid":
        cta_block = f"""
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin:28px 0;">
                  <tr><td align="center">
                    <a href="{payment_url}"
                       style="display:inline-block;background-color:#009EA1;color:#ffffff;
                              font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;font-weight:700;
                              text-decoration:none;padding:14px 40px;border-radius:8px;">
                      {payment_button_text}
                    </a>
                  </td></tr>
                </table>
        """

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Invoice {invoice_number}</title></head>
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

      <!-- STATUS BADGE -->
      <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
        <tr><td>
          <h2 style="margin:0 0 6px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:20px;color:#009EA1;">
            Invoice #{invoice_number}
          </h2>
          <span style="display:inline-block;background:{s['bg']};color:{s['color']};font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;
                       font-size:12px;font-weight:700;padding:4px 14px;border-radius:20px;">
            {s['label']}
          </span>
        </td></tr>
      </table>

      <!-- DETAILS -->
      <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
             style="background:#F7FBFF;border-radius:10px;border:1px solid #E0EBF5;margin:20px 0;">
        <tr><td style="padding:12px 15px 4px;font-family:Roboto,Tahoma,Verdana,Segoe,sans-serif;font-size:14px;font-weight:700;color:#009EA1;">
          Invoice Details
        </td></tr>
        {details}
      </table>

      {items_html}

      {cta_block}

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
