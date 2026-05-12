from app.modules.auth.enums.common import MessageCategory
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.configs.config import settings
from app.modules.core.services.response.response_service import ResponseService

def email_template_with_click_button(mail_title_message: str, mail_message: str,action_button_url:str,action_button_text:str, second_mail_message: str = "", mail_note: str = "",accept_language:str = DEFAULT_LANGUAGE) -> str:
    
    PHONE_NUMBER_TITLE = ResponseService.get_response_message(MessageCategory.EMAIL_TEMPLATE, "PHONE_NUMBER_TITLE", accept_language)
    EMAIL_TITLE = ResponseService.get_response_message(MessageCategory.EMAIL_TEMPLATE, "EMAIL_TITLE", accept_language)
    ADDRESS_TITLE = ResponseService.get_response_message(MessageCategory.EMAIL_TEMPLATE, "ADDRESS_TITLE", accept_language)
    CORDIAL_TITLE = ResponseService.get_response_message(MessageCategory.EMAIL_TEMPLATE, "CORDIAL_TITLE", accept_language)
    FOR_ALL_ASSISTANCE = ResponseService.get_response_message(MessageCategory.EMAIL_TEMPLATE, "FOR_ALL_ASSISTANCE", accept_language)
    ADDRESS_VALUE = ResponseService.get_response_message(MessageCategory.EMAIL_TEMPLATE, "ADDRESS_VALUE", accept_language)
    SENAT_DIGIT_APPS_FILE_SYSTEM_URL = f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/static/apps/senat_digit-app.png"
    
    return f"""
     <table
        width="100%"
        border="0"
        cellpadding="0"
        cellspacing="0"
        role="presentation"
        style="background-color: #F0F8FF"
        >
        <tbody>
            <tr>
                <table
                align="center"
                width="100%"
                border="0"
                cellpadding="0"
                cellspacing="0"
                role="presentation"
                >
                <tbody>
                    <tr>
                    <td>
                        <table
                        class="m_-3509855705363049637row-content m_-3509855705363049637stack"
                        align="center"
                        border="0"
                        cellpadding="0"
                        cellspacing="0"
                        role="presentation"
                        style="background-color: #fffff; color: #000000; width: 700px"
                        width="700px"
                        >
                        <tbody>
                            <tr>
                            <td
                                class="m_-3509855705363049637column"
                                width="100%"
                                style="
                                font-weight: 400;
                                text-align: left;
                                vertical-align: top;
                                padding-top: 25px;
                                padding-bottom: 25px;
                                border-top: 0px;
                                border-right: 0px;
                                border-bottom: 0px;
                                border-left: 0px;
                                "
                            >
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                >
                                <tbody>
                                    <tr>
                                    <td
                                        style="
                                        width: 100%;
                                        padding-right: 0px;
                                        padding-left: 0px;
                                        "
                                    >
                                        <div align="center" style="line-height: 10px">
                                        <a
                                            href="https://senat_digit.digipublic.app/"
                                            style="outline: none"
                                            target="_blank"
                                        >
                                            <img 
                                            src="{SENAT_DIGIT_APPS_FILE_SYSTEM_URL}"
                                            style="
                                                display: block;
                                                height: auto;
                                                border: 0;
                                                width: 120px;
                                                max-width: 100%;
                                            "
                                            width="205"
                                            alt="SenatDigit Apps Logo"
                                            title="SenatDigit Apps Logo"
                                            class="CToWUd"
                                            data-bit="iit"
                                            />
                                        </a>
                                        </div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                            </td>
                            </tr>
                        </tbody>
                        </table>
                    </td>
                    </tr>
                </tbody>
                </table>
                <table
                align="center"
                width="100%"
                border="0"
                cellpadding="0"
                cellspacing="0"
                role="presentation"
                >
                <tbody>
                    <tr>
                    <td>
                        <table
                        class="m_-3509855705363049637row-content m_-3509855705363049637stack"
                        align="center"
                        border="0"
                        cellpadding="0"
                        cellspacing="0"
                        role="presentation"
                        style="background-color: #fffff; color: #000000; width: 700px"
                        width="700"
                        >
                        <tbody>
                            <tr>
                            <td
                                class="m_-3509855705363049637column"
                                width="8.333333333333334%"
                                style="
                                font-weight: 400;
                                text-align: left;
                                vertical-align: top;
                                border-top: 0px;
                                border-right: 0px;
                                border-bottom: 0px;
                                border-left: 0px;
                                "
                            >
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                >
                                <tbody>
                                    <tr>
                                    <td
                                        style="
                                        padding-right: 0px;
                                        padding-bottom: 5px;
                                        padding-left: 0px;
                                        padding-top: 5px;
                                        "
                                    >
                                        <div></div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                            </td>
                            <td
                                class="m_-3509855705363049637column"
                                width="83.33333333333333%"
                                style="
                                border-radius: 5px;
                                font-weight: 400;
                                text-align: left;
                                vertical-align: top;
                                background-color: #aba;
                                padding-left: 50px;
                                padding-right: 50px;
                                border-top: 0px;
                                border-right: 0px;
                                border-bottom: 0px;
                                border-left: 0px;
                                "
                            >
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                >
                                <tbody>
                                    <tr>
                                    <td
                                        style="
                                        padding-bottom: 60px;
                                        text-align: center;
                                        width: 100%;
                                        "
                                    >
                                        <h1
                                        style="
                                            margin: 0;
                                            color: #009ea1;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                            sans-serif;
                                            font-size: 20px;
                                            font-weight: 400;
                                            letter-spacing: normal;
                                            line-height: 120%;
                                            text-align: center;
                                            margin-top: 0;
                                            margin-bottom: 0;
                                        "
                                        ></h1>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                >
                                <tbody>
                                    <tr>
                                    <td style="text-align: center; width: 100%">
                                        <h1
                                        style="
                                            margin: 0;
                                            color: #009ea1;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                            sans-serif;
                                            font-size: 18px;
                                            font-weight: 700;
                                            letter-spacing: normal;
                                            line-height: 120%;
                                            text-align: left;
                                            margin-top: 0;
                                            margin-bottom: 0;
                                        "
                                        >
                                        <span>{mail_title_message} ,</span>
                                        </h1>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                style="word-break: break-word; padding-top: 15px"
                                >
                                <tbody>
                                    <tr>
                                    <td
                                        style="padding-bottom: 20px; padding-top: 10px"
                                    >
                                        <div
                                        style="
                                            color: #320100;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                            sans-serif;
                                            font-size: 14px;
                                            font-weight: 400;
                                            letter-spacing: 0px;
                                            line-height: 150%;
                                            text-align: left;
                                        "
                                        >
                                        <p style="margin: 0">{mail_message}</p>
                                        </div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>

                                <table style="margin-bottom: 35px;margin-top: 25px;" width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation">
                                    <tbody>
                                      <tr>
                                        <td style="text-align:center">
                                          <div align="center">
                                            <a href="{action_button_url}" style="text-decoration:none;display:inline-block;color:#fafafa;background-color:#019EA1;border-radius:8px;width:auto;border-top:1px solid #019EA1;font-weight:700;border-right:1px solid #019EA1;border-bottom:1px solid #019EA1;border-left:1px solid #019EA1;padding-top:10px;padding-bottom:10px;font-family:'Roboto',Tahoma,Verdana,Segoe,sans-serif;text-align:center;word-break:keep-all" target="_blank">
                                              <span style="padding-left:60px;padding-right:60px;font-size:16px;display:inline-block;letter-spacing:normal">
                                                <span style="font-size:16px;line-height:2;word-break:break-word">{action_button_text}</span>
                                              </span>
                                            </a>
                                          </div>
                                        </td>
                                      </tr>
                                    </tbody>
                                  </table>

                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                style="word-break: break-word"
                                >
                                <tbody>
                                    <tr>
                                    <td style="padding-top: 0px">
                                        <div
                                        style="
                                            color: #320100;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                            sans-serif;
                                            font-size: 14px;
                                            font-weight: 400;
                                            letter-spacing: 0px;
                                            line-height: 150%;
                                            text-align: left;
                                        "
                                        >
                                        <p style="margin: 0">
                                            {second_mail_message}
                                        </p>
                                        </div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                style="word-break: break-word"
                                >
                                <tbody>
                                    <tr>
                                    <td style="padding-top: 35px">
                                        <div
                                        style="
                                            background: #Fx0F8FF;
                                            padding: 8px; 
                                            color: #320100;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                            sans-serif;
                                            font-size: 14px;
                                            font-weight: 400;
                                            letter-spacing: 0px;
                                            line-height: 150%;
                                            text-align: left;
                                        "
                                        >
                                        <p style="margin: 0; margin-bottom: 0px">
                                            {FOR_ALL_ASSISTANCE}
                                        </p>
                                        <p style="margin: 0">
                                            <a
                                            href="mailto:support@senat_digit.digipublic.app"
                                            title="Assistance"
                                            rel="noopener"
                                            style="
                                                text-decoration: none;
                                                color: #009ea1;
                                            "
                                            target="_blank"
                                            >support@senat_digit.digipublic.app</a
                                            >
                                        </p>
                                        </div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                                
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                style="word-break: break-word"
                                >
                                <tbody>
                                    <tr>
                                    <td
                                        style="
                                        padding-bottom: 75px;
                                        padding-right: 10px;
                                        padding-top: 15px;
                                        "
                                    >
                                        <div
                                        style="
                                            padding-left: 8px;
                                            border-leftx: 2px solid;
                                            color: #1d2144;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                            sans-serif;
                                            font-size: 14px;
                                            font-weight: 400;
                                            letter-spacing: 0px;
                                            line-height: 120%;
                                            text-align: left;
                                        "
                                        >
                                        <hr style="border:.1px solid #d7d8d7;">
                                        <p
                                            style="
                                            margin: 0;
                                            margin-top: 25px;
                                            margin-bottom: 5px;
                                            color: #009ea1;
                                            "
                                        >
                                            {CORDIAL_TITLE}.
                                        </p>
                                        <p style="margin: 0">
                                            <strong>SenatDigit Apps Team</strong>
                                        </p>
                                        </div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                            </td>
                            <td
                                class="m_-3509855705363049637column"
                                width="8.333333333333334%"
                                style="
                                font-weight: 400;
                                text-align: left;
                                vertical-align: top;
                                border-top: 0px;
                                border-right: 0px;
                                border-bottom: 0px;
                                border-left: 0px;
                                "
                            >
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                >
                                <tbody>
                                    <tr>
                                    <td
                                        style="
                                        padding-right: 0px;
                                        padding-bottom: 5px;
                                        padding-left: 0px;
                                        padding-top: 5px;
                                        "
                                    >
                                        <div></div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                            </td>
                            </tr>
                        </tbody>
                        </table>
                    </td>
                    </tr>
                    

                    <!-- START BOTTOM AREA -->
                    <tr>
                        <td>
                        <table
                            class="m_-3509855705363049637row-content m_-3509855705363049637stack"
                            align="center"
                            border="0"
                            cellpadding="0"
                            cellspacing="0"
                            role="presentation"
                            style="background-color: #fffff; color: #000000; width: 700px;padding-top:40px;"
                            width="700"
                        >
                            <tbody>
                            <tr>
                                <td
                                class="m_-3509855705363049637column"
                                width="8.333333333333334%"
                                style="
                                    font-weight: 400;
                                    text-align: left;
                                    vertical-align: top;
                                    border-top: 0px;
                                    border-right: 0px;
                                    border-bottom: 0px;
                                    border-left: 0px;
                                "
                                >
                                <table
                                    width="100%"
                                    border="0"
                                    cellpadding="0"
                                    cellspacing="0"
                                    role="presentation"
                                >
                                    <tbody>
                                    <tr>
                                        <td
                                        style="
                                            padding-right: 0px;
                                            padding-bottom: 5px;
                                            padding-left: 0px;
                                            padding-top: 5px;
                                        "
                                        >
                                        <div></div>
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
                                </td>
                                <td
                                class="m_-3509855705363049637column"
                                width="83.33333333333333%"
                                style="

                                    border-radius: 5px;
                                    font-weight: 400;
                                    text-align: left;
                                    vertical-align: top;
                                    background-color: #0D3742;
                                    padding-left: 50px;
                                    padding-right: 50px;
                                    border-top: 0px;
                                    border-right: 0px;
                                    border-bottom: 0px;
                                    border-left: 0px;
                                "
                                >
                                <table
                                    width="100%"
                                    border="0"
                                    cellpadding="0"
                                    cellspacing="0"
                                    role="presentation"
                                >
                                    <tbody>
                                    <tr>
                                        <td
                                        style="
                                            padding-bottom: 30px;
                                            text-align: center;
                                            width: 100%;
                                        "
                                        >
                                        <h1
                                            style="
                                            margin: 0;
                                            color: #009ea1;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                                sans-serif;
                                            font-size: 20px;
                                            font-weight: 400;
                                            letter-spacing: normal;
                                            line-height: 120%;
                                            text-align: center;
                                            margin-top: 0;
                                            margin-bottom: 0;
                                            "
                                        ></h1>
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
                                <table
                                    width="100%"
                                    border="0"
                                    cellpadding="0"
                                    cellspacing="0"
                                    role="presentation"
                                >
                                    <tbody>
                                    <tr>
                                        <td style="text-align: center; width: 100%">
                                        <h1
                                            style="
                                            margin: 0;
                                            color: #009ea1;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                                sans-serif;
                                            font-size: 18px;
                                            font-weight: 700;
                                            text-align: center;
                                            letter-spacing: normal;
                                            line-height: 120%;
                                            text-align: left;
                                            margin-top: 0;
                                            margin-bottom: 0;
                                            "
                                        >
                                        SenatDigit
                                        </h1>
                                        <!-- <hr style="border:.1px solid #d7d8d7;"> -->
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
                                <table
                                    width="100%"
                                    border="0"
                                    cellpadding="0"
                                    cellspacing="0"
                                    role="presentation"
                                    style="word-break: break-word; padding-top: 15px"
                                >
                                    <tbody>
                                    <tr>
                                        <td
                                        style="padding-bottom: 15px; padding-top: 0px"
                                        >
                                        <div
                                            style="
                                            color: #320100;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                                sans-serif;
                                            font-size: 14px;
                                            font-weight: 400;
                                            letter-spacing: 0px;
                                            line-height: 150%;
                                            text-align: left;
                                            "
                                        >
                                            <p style="margin: 0;color: #dfdbdb;">{EMAIL_TITLE}:</p>
                                            <p style="margin: 0;color: #009ea1;">
                                                info@senat_digit.digipublic.app
                                            </p>
                                        </div>
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
        
                                <table
                                    width="100%"
                                    border="0"
                                    cellpadding="0"
                                    cellspacing="0"
                                    role="presentation"
                                    style="word-break: break-word"
                                >
                                    <tbody>
                                    <tr>
                                        <td style="padding-bottom: 15px; padding-top: 0px">
                                        <div
                                            style="
                                            color: #320100;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                                sans-serif;
                                            font-size: 14px;
                                            font-weight: 400;
                                            letter-spacing: 0px;
                                            line-height: 150%;
                                            text-align: left;
                                            "
                                        >
                                            <p style="margin: 0;color: #dfdbdb;">
                                            {PHONE_NUMBER_TITLE}:
                                            </p>
                                            <p style="margin: 0;color: #009ea1;">
                                                +243 81 333 87 77
                                            </p>
                                        </div>
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
                                <table
                                    width="100%"
                                    border="0"
                                    cellpadding="0"
                                    cellspacing="0"
                                    role="presentation"
                                    style="word-break: break-word"
                                >
                                    <tbody>
                                    <tr>
                                        <td style="padding-top: 5px;padding-bottom: 35px;">
                                        <div
                                            style="
                                            background: #Fx0F8FF;
                                            color: #320100;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                                sans-serif;
                                            font-size: 14px;
                                            font-weight: 400;
                                            letter-spacing: 0px;
                                            line-height: 150%;
                                            text-align: left;
                                            "
                                        >
                                            <p style="margin: 0; margin-bottom: 0px;color: #dfdbdb;">
                                            {ADDRESS_TITLE} :
                                            </p>
                                            <p style="margin: 0;color: #009ea1;">
                                               {ADDRESS_VALUE}
                                            </p>
                                        </div>
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
                                
                                
                                </td>
                                <td
                                class="m_-3509855705363049637column"
                                width="8.333333333333334%"
                                style="
                                    font-weight: 400;
                                    text-align: left;
                                    vertical-align: top;
                                    border-top: 0px;
                                    border-right: 0px;
                                    border-bottom: 0px;
                                    border-left: 0px;
                                "
                                >
                                <table
                                    width="100%"
                                    border="0"
                                    cellpadding="0"
                                    cellspacing="0"
                                    role="presentation"
                                >
                                    <tbody>
                                    <tr>
                                        <td
                                        style="
                                            padding-right: 0px;
                                            padding-bottom: 5px;
                                            padding-left: 0px;
                                            padding-top: 5px;
                                        "
                                        >
                                        <div></div>
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
                                </td>
                            </tr>
                            </tbody>
                        </table>
                        </td>
                    </tr>
                    <!-- END BOTTOM AREA -->

                </tbody>
                </table>
                <table
                align="center"
                width="100%"
                border="0"
                cellpadding="0"
                cellspacing="0"
                role="presentation"
                >
                <tbody>
                    <tr>
                    <td>
                        <table
                        class="m_-3509855705363049637row-content m_-3509855705363049637stack"
                        align="center"
                        border="0"
                        cellpadding="0"
                        cellspacing="0"
                        role="presentation"
                        style="background-color: #fffff; color: #000000; width: 700px"
                        width="700"
                        >
                        <tbody>
                            <tr>
                            <td
                                class="m_-3509855705363049637column"
                                width="16.666666666666668%"
                                style="
                                font-weight: 400;
                                text-align: left;
                                vertical-align: top;
                                border-top: 0px;
                                border-right: 0px;
                                border-bottom: 0px;
                                border-left: 0px;
                                "
                            >
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                >
                                <tbody>
                                    <tr>
                                    <td>
                                        <div></div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                            </td>
                            <td
                                class="m_-3509855705363049637column"
                                width="66.66666666666667%"
                                style="
                                font-weight: 400;
                                text-align: left;
                                vertical-align: top;
                                border-top: 0px;
                                border-right: 0px;
                                border-bottom: 0px;
                                border-left: 0px;
                                "
                            >
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                style="word-break: break-word"
                                >
                                <tbody>
                                    <tr>
                                    <td
                                        style="
                                        padding-bottom: 60px;
                                        padding-left: 10px;
                                        padding-right: 10px;
                                        padding-top: 60px;
                                        "
                                    >
                                        <div
                                        style="
                                            color: #fafafax;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                            sans-serif;
                                            font-size: 14px;
                                            font-weight: 400;
                                            letter-spacing: 0px;
                                            line-height: 150%;
                                            text-align: center;
                                        "
                                        >
                                        <p style="margin: 0; margin-bottom: 16px">
                                            {mail_note}.
                                        </p>
                                        <p style="margin: 0"></p>
                                        </div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                            </td>
                            <td
                                class="m_-3509855705363049637column"
                                width="16.666666666666668%"
                                style="
                                font-weight: 400;
                                text-align: left;
                                vertical-align: top;
                                border-top: 0px;
                                border-right: 0px;
                                border-bottom: 0px;
                                border-left: 0px;
                                "
                            >
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                >
                                <tbody>
                                    <tr>
                                    <td>
                                        <div></div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                            </td>
                            </tr>
                        </tbody>
                        </table>
                    </td>
                    </tr>
                </tbody>
                </table>
                <table
                align="center"
                width="100%"
                border="0"
                cellpadding="0"
                cellspacing="0"
                role="presentation"
                >
                <tbody>
                    <tr>
                    <td>
                        <table
                        class="m_-3509855705363049637row-content m_-3509855705363049637stack"
                        align="center"
                        border="0"
                        cellpadding="0"
                        cellspacing="0"
                        role="presentation"
                        style="background-color: #fffff; color: #000000; width: 700px"
                        width="700"
                        >
                        <tbody>
                            <tr>
                            <td
                                class="m_-3509855705363049637column"
                                width="100%"
                                style="
                                font-weight: 400;
                                text-align: left;
                                vertical-align: top;
                                padding-top: 5px;
                                padding-bottom: 5px;
                                border-top: 0px;
                                border-right: 0px;
                                border-bottom: 0px;
                                border-left: 0px;
                                "
                            >
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                >
                                <tbody>
                                    <tr>
                                    <td>
                                        <div></div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                            </td>
                            </tr>
                        </tbody>
                        </table>
                    </td>
                    </tr>
                </tbody>
                </table>
            </td>
            </tr>
        </tbody>
        </table>
    """

def email_template(mail_title_message: str, mail_message: str, second_mail_message: str = "", mail_note: str = "",accept_language:str = DEFAULT_LANGUAGE) -> str:
    
    PHONE_NUMBER_TITLE = ResponseService.get_response_message(MessageCategory.EMAIL_TEMPLATE, "PHONE_NUMBER_TITLE", accept_language)
    EMAIL_TITLE = ResponseService.get_response_message(MessageCategory.EMAIL_TEMPLATE, "EMAIL_TITLE", accept_language)
    ADDRESS_TITLE = ResponseService.get_response_message(MessageCategory.EMAIL_TEMPLATE, "ADDRESS_TITLE", accept_language)
    CORDIAL_TITLE = ResponseService.get_response_message(MessageCategory.EMAIL_TEMPLATE, "CORDIAL_TITLE", accept_language)
    FOR_ALL_ASSISTANCE = ResponseService.get_response_message(MessageCategory.EMAIL_TEMPLATE, "FOR_ALL_ASSISTANCE", accept_language)
    ADDRESS_VALUE = ResponseService.get_response_message(MessageCategory.EMAIL_TEMPLATE, "ADDRESS_VALUE", accept_language)
    SENAT_DIGIT_APPS_FILE_SYSTEM_URL = f"{settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL}/static/files/apps/senat_digit-app.png"
    
    return f"""
    <table
        width="100%"
        border="0"
        cellpadding="0"
        cellspacing="0"
        role="presentation"
        style="background-color: #F0F8FF"
        >
        <tbody>
            <tr>
                <table
                align="center"
                width="100%"
                border="0"
                cellpadding="0"
                cellspacing="0"
                role="presentation"
                >
                <tbody>
                    <tr>
                    <td>
                        <table
                        class="m_-3509855705363049637row-content m_-3509855705363049637stack"
                        align="center"
                        border="0"
                        cellpadding="0"
                        cellspacing="0"
                        role="presentation"
                        style="background-color: #fffff; color: #000000; width: 700px"
                        width="700px"
                        >
                        <tbody>
                            <tr>
                            <td
                                class="m_-3509855705363049637column"
                                width="100%"
                                style="
                                font-weight: 400;
                                text-align: left;
                                vertical-align: top;
                                padding-top: 25px;
                                padding-bottom: 25px;
                                border-top: 0px;
                                border-right: 0px;
                                border-bottom: 0px;
                                border-left: 0px;
                                "
                            >
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                >
                                <tbody>
                                    <tr>
                                    <td
                                        style="
                                        width: 100%;
                                        padding-right: 0px;
                                        padding-left: 0px;
                                        "
                                    >
                                        <div align="center" style="line-height: 10px">
                                        <a
                                            href="https://senat_digit.digipublic.app/"
                                            style="outline: none"
                                            target="_blank"
                                        >
                                            <img
                                            src="{SENAT_DIGIT_APPS_FILE_SYSTEM_URL}"
                                            style="
                                                display: block;
                                                height: auto;
                                                border: 0;
                                                width: 120px;
                                                max-width: 100%;
                                            "
                                            width="205"
                                            alt="SenatDigit Logo"
                                            title="SenatDigit Logo"
                                            class="CToWUd"
                                            data-bit="iit"
                                            />
                                        </a>
                                        </div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                            </td>
                            </tr>
                        </tbody>
                        </table>
                    </td>
                    </tr>
                </tbody>
                </table>
                <table
                align="center"
                width="100%"
                border="0"
                cellpadding="0"
                cellspacing="0"
                role="presentation"
                >
                <tbody>
                    <tr>
                    <td>
                        <table
                        class="m_-3509855705363049637row-content m_-3509855705363049637stack"
                        align="center"
                        border="0"
                        cellpadding="0"
                        cellspacing="0"
                        role="presentation"
                        style="background-color: #fffff; color: #000000; width: 700px"
                        width="700"
                        >
                        <tbody>
                            <tr>
                            <td
                                class="m_-3509855705363049637column"
                                width="8.333333333333334%"
                                style="
                                font-weight: 400;
                                text-align: left;
                                vertical-align: top;
                                border-top: 0px;
                                border-right: 0px;
                                border-bottom: 0px;
                                border-left: 0px;
                                "
                            >
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                >
                                <tbody>
                                    <tr>
                                    <td
                                        style="
                                        padding-right: 0px;
                                        padding-bottom: 5px;
                                        padding-left: 0px;
                                        padding-top: 5px;
                                        "
                                    >
                                        <div></div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                            </td>
                            <td
                                class="m_-3509855705363049637column"
                                width="83.33333333333333%"
                                style="
                                border-radius: 5px;
                                font-weight: 400;
                                text-align: left;
                                vertical-align: top;
                                background-color: #aba;
                                padding-left: 50px;
                                padding-right: 50px;
                                border-top: 0px;
                                border-right: 0px;
                                border-bottom: 0px;
                                border-left: 0px;
                                "
                            >
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                >
                                <tbody>
                                    <tr>
                                    <td
                                        style="
                                        padding-bottom: 60px;
                                        text-align: center;
                                        width: 100%;
                                        "
                                    >
                                        <h1
                                        style="
                                            margin: 0;
                                            color: #009ea1;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                            sans-serif;
                                            font-size: 20px;
                                            font-weight: 400;
                                            letter-spacing: normal;
                                            line-height: 120%;
                                            text-align: center;
                                            margin-top: 0;
                                            margin-bottom: 0;
                                        "
                                        ></h1>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                >
                                <tbody>
                                    <tr>
                                    <td style="text-align: center; width: 100%">
                                        <h1
                                        style="
                                            margin: 0;
                                            color: #009ea1;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                            sans-serif;
                                            font-size: 18px;
                                            font-weight: 700;
                                            letter-spacing: normal;
                                            line-height: 120%;
                                            text-align: left;
                                            margin-top: 0;
                                            margin-bottom: 0;
                                        "
                                        >
                                        <span>{mail_title_message} ,</span>
                                        </h1>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                style="word-break: break-word; padding-top: 15px"
                                >
                                <tbody>
                                    <tr>
                                    <td
                                        style="padding-bottom: 20px; padding-top: 10px"
                                    >
                                        <div
                                        style="
                                            color: #320100;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                            sans-serif;
                                            font-size: 14px;
                                            font-weight: 400;
                                            letter-spacing: 0px;
                                            line-height: 150%;
                                            text-align: left;
                                        "
                                        >
                                        <p style="margin: 0">{mail_message}</p>
                                        </div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>

                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                style="word-break: break-word"
                                >
                                <tbody>
                                    <tr>
                                    <td style="padding-top: 0px">
                                        <div
                                        style="
                                            color: #320100;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                            sans-serif;
                                            font-size: 14px;
                                            font-weight: 400;
                                            letter-spacing: 0px;
                                            line-height: 150%;
                                            text-align: left;
                                        "
                                        >
                                        <p style="margin: 0">
                                            {second_mail_message}
                                        </p>
                                        </div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                style="word-break: break-word"
                                >
                                <tbody>
                                    <tr>
                                    <td style="padding-top: 35px">
                                        <div
                                        style="
                                            background: #Fx0F8FF;
                                            padding: 8px; 
                                            color: #320100;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                            sans-serif;
                                            font-size: 14px;
                                            font-weight: 400;
                                            letter-spacing: 0px;
                                            line-height: 150%;
                                            text-align: left;
                                        "
                                        >
                                        <p style="margin: 0; margin-bottom: 0px">
                                            {FOR_ALL_ASSISTANCE}
                                        </p>
                                        <p style="margin: 0">
                                            <a
                                            href="mailto:support@senat_digit.digipublic.app"
                                            title="Assistance"
                                            rel="noopener"
                                            style="
                                                text-decoration: none;
                                                color: #009ea1;
                                            "
                                            target="_blank"
                                            >support@senat_digit.digipublic.app</a
                                            >
                                        </p>
                                        </div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                                
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                style="word-break: break-word"
                                >
                                <tbody>
                                    <tr>
                                    <td
                                        style="
                                        padding-bottom: 75px;
                                        padding-right: 10px;
                                        padding-top: 15px;
                                        "
                                    >
                                        <div
                                        style="
                                            padding-left: 8px;
                                            border-leftx: 2px solid;
                                            color: #1d2144;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                            sans-serif;
                                            font-size: 14px;
                                            font-weight: 400;
                                            letter-spacing: 0px;
                                            line-height: 120%;
                                            text-align: left;
                                        "
                                        >
                                        <hr style="border:.1px solid #d7d8d7;">
                                        <p
                                            style="
                                            margin: 0;
                                            margin-top: 25px;
                                            margin-bottom: 5px;
                                            color: #009ea1;
                                            "
                                        >
                                            {CORDIAL_TITLE}.
                                        </p>
                                        <p style="margin: 0">
                                            <strong>SenatDigit Apps Team</strong>
                                        </p>
                                        </div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                            </td>
                            <td
                                class="m_-3509855705363049637column"
                                width="8.333333333333334%"
                                style="
                                font-weight: 400;
                                text-align: left;
                                vertical-align: top;
                                border-top: 0px;
                                border-right: 0px;
                                border-bottom: 0px;
                                border-left: 0px;
                                "
                            >
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                >
                                <tbody>
                                    <tr>
                                    <td
                                        style="
                                        padding-right: 0px;
                                        padding-bottom: 5px;
                                        padding-left: 0px;
                                        padding-top: 5px;
                                        "
                                    >
                                        <div></div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                            </td>
                            </tr>
                        </tbody>
                        </table>
                    </td>
                    </tr>
                    

                    <!-- START BOTTOM AREA -->
                    <tr>
                        <td>
                        <table
                            class="m_-3509855705363049637row-content m_-3509855705363049637stack"
                            align="center"
                            border="0"
                            cellpadding="0"
                            cellspacing="0"
                            role="presentation"
                            style="background-color: #fffff; color: #000000; width: 700px;padding-top:40px;"
                            width="700"
                        >
                            <tbody>
                            <tr>
                                <td
                                class="m_-3509855705363049637column"
                                width="8.333333333333334%"
                                style="
                                    font-weight: 400;
                                    text-align: left;
                                    vertical-align: top;
                                    border-top: 0px;
                                    border-right: 0px;
                                    border-bottom: 0px;
                                    border-left: 0px;
                                "
                                >
                                <table
                                    width="100%"
                                    border="0"
                                    cellpadding="0"
                                    cellspacing="0"
                                    role="presentation"
                                >
                                    <tbody>
                                    <tr>
                                        <td
                                        style="
                                            padding-right: 0px;
                                            padding-bottom: 5px;
                                            padding-left: 0px;
                                            padding-top: 5px;
                                        "
                                        >
                                        <div></div>
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
                                </td>
                                <td
                                class="m_-3509855705363049637column"
                                width="83.33333333333333%"
                                style="

                                    border-radius: 5px;
                                    font-weight: 400;
                                    text-align: left;
                                    vertical-align: top;
                                    background-color: #0D3742;
                                    padding-left: 50px;
                                    padding-right: 50px;
                                    border-top: 0px;
                                    border-right: 0px;
                                    border-bottom: 0px;
                                    border-left: 0px;
                                "
                                >
                                <table
                                    width="100%"
                                    border="0"
                                    cellpadding="0"
                                    cellspacing="0"
                                    role="presentation"
                                >
                                    <tbody>
                                    <tr>
                                        <td
                                        style="
                                            padding-bottom: 30px;
                                            text-align: center;
                                            width: 100%;
                                        "
                                        >
                                        <h1
                                            style="
                                            margin: 0;
                                            color: #009ea1;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                                sans-serif;
                                            font-size: 20px;
                                            font-weight: 400;
                                            letter-spacing: normal;
                                            line-height: 120%;
                                            text-align: center;
                                            margin-top: 0;
                                            margin-bottom: 0;
                                            "
                                        ></h1>
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
                                <table
                                    width="100%"
                                    border="0"
                                    cellpadding="0"
                                    cellspacing="0"
                                    role="presentation"
                                >
                                    <tbody>
                                    <tr>
                                        <td style="text-align: center; width: 100%">
                                        <h1
                                            style="
                                            margin: 0;
                                            color: #009ea1;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                                sans-serif;
                                            font-size: 18px;
                                            font-weight: 700;
                                            text-align: center;
                                            letter-spacing: normal;
                                            line-height: 120%;
                                            text-align: left;
                                            margin-top: 0;
                                            margin-bottom: 0;
                                            "
                                        >
                                        SenatDigit
                                        </h1>
                                        <!-- <hr style="border:.1px solid #d7d8d7;"> -->
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
                                <table
                                    width="100%"
                                    border="0"
                                    cellpadding="0"
                                    cellspacing="0"
                                    role="presentation"
                                    style="word-break: break-word; padding-top: 15px"
                                >
                                    <tbody>
                                    <tr>
                                        <td
                                        style="padding-bottom: 15px; padding-top: 0px"
                                        >
                                        <div
                                            style="
                                            color: #320100;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                                sans-serif;
                                            font-size: 14px;
                                            font-weight: 400;
                                            letter-spacing: 0px;
                                            line-height: 150%;
                                            text-align: left;
                                            "
                                        >
                                            <p style="margin: 0;color: #dfdbdb;">{EMAIL_TITLE}:</p>
                                            <p style="margin: 0;color: #009ea1;">
                                                info@senat_digit.digipublic.app
                                            </p>
                                        </div>
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
        
                                <table
                                    width="100%"
                                    border="0"
                                    cellpadding="0"
                                    cellspacing="0"
                                    role="presentation"
                                    style="word-break: break-word"
                                >
                                    <tbody>
                                    <tr>
                                        <td style="padding-bottom: 15px; padding-top: 0px">
                                        <div
                                            style="
                                            color: #320100;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                                sans-serif;
                                            font-size: 14px;
                                            font-weight: 400;
                                            letter-spacing: 0px;
                                            line-height: 150%;
                                            text-align: left;
                                            "
                                        >
                                            <p style="margin: 0;color: #dfdbdb;">
                                            {PHONE_NUMBER_TITLE}:
                                            </p>
                                            <p style="margin: 0;color: #009ea1;">
                                                +243 81 333 87 77
                                            </p>
                                        </div>
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
                                <table
                                    width="100%"
                                    border="0"
                                    cellpadding="0"
                                    cellspacing="0"
                                    role="presentation"
                                    style="word-break: break-word"
                                >
                                    <tbody>
                                    <tr>
                                        <td style="padding-top: 5px;padding-bottom: 35px;">
                                        <div
                                            style="
                                            background: #Fx0F8FF;
                                            color: #320100;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                                sans-serif;
                                            font-size: 14px;
                                            font-weight: 400;
                                            letter-spacing: 0px;
                                            line-height: 150%;
                                            text-align: left;
                                            "
                                        >
                                            <p style="margin: 0; margin-bottom: 0px;color: #dfdbdb;">
                                            {ADDRESS_TITLE} :
                                            </p>
                                            <p style="margin: 0;color: #009ea1;">
                                               {ADDRESS_VALUE}
                                            </p>
                                        </div>
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
                                
                                
                                </td>
                                <td
                                class="m_-3509855705363049637column"
                                width="8.333333333333334%"
                                style="
                                    font-weight: 400;
                                    text-align: left;
                                    vertical-align: top;
                                    border-top: 0px;
                                    border-right: 0px;
                                    border-bottom: 0px;
                                    border-left: 0px;
                                "
                                >
                                <table
                                    width="100%"
                                    border="0"
                                    cellpadding="0"
                                    cellspacing="0"
                                    role="presentation"
                                >
                                    <tbody>
                                    <tr>
                                        <td
                                        style="
                                            padding-right: 0px;
                                            padding-bottom: 5px;
                                            padding-left: 0px;
                                            padding-top: 5px;
                                        "
                                        >
                                        <div></div>
                                        </td>
                                    </tr>
                                    </tbody>
                                </table>
                                </td>
                            </tr>
                            </tbody>
                        </table>
                        </td>
                    </tr>
                    <!-- END BOTTOM AREA -->

                </tbody>
                </table>
                <table
                align="center"
                width="100%"
                border="0"
                cellpadding="0"
                cellspacing="0"
                role="presentation"
                >
                <tbody>
                    <tr>
                    <td>
                        <table
                        class="m_-3509855705363049637row-content m_-3509855705363049637stack"
                        align="center"
                        border="0"
                        cellpadding="0"
                        cellspacing="0"
                        role="presentation"
                        style="background-color: #fffff; color: #000000; width: 700px"
                        width="700"
                        >
                        <tbody>
                            <tr>
                            <td
                                class="m_-3509855705363049637column"
                                width="16.666666666666668%"
                                style="
                                font-weight: 400;
                                text-align: left;
                                vertical-align: top;
                                border-top: 0px;
                                border-right: 0px;
                                border-bottom: 0px;
                                border-left: 0px;
                                "
                            >
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                >
                                <tbody>
                                    <tr>
                                    <td>
                                        <div></div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                            </td>
                            <td
                                class="m_-3509855705363049637column"
                                width="66.66666666666667%"
                                style="
                                font-weight: 400;
                                text-align: left;
                                vertical-align: top;
                                border-top: 0px;
                                border-right: 0px;
                                border-bottom: 0px;
                                border-left: 0px;
                                "
                            >
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                style="word-break: break-word"
                                >
                                <tbody>
                                    <tr>
                                    <td
                                        style="
                                        padding-bottom: 60px;
                                        padding-left: 10px;
                                        padding-right: 10px;
                                        padding-top: 60px;
                                        "
                                    >
                                        <div
                                        style="
                                            color: #fafafax;
                                            direction: ltr;
                                            font-family: Roboto, Tahoma, Verdana, Segoe,
                                            sans-serif;
                                            font-size: 14px;
                                            font-weight: 400;
                                            letter-spacing: 0px;
                                            line-height: 150%;
                                            text-align: center;
                                        "
                                        >
                                        <p style="margin: 0; margin-bottom: 16px">
                                            {mail_note}.
                                        </p>
                                        <p style="margin: 0"></p>
                                        </div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                            </td>
                            <td
                                class="m_-3509855705363049637column"
                                width="16.666666666666668%"
                                style="
                                font-weight: 400;
                                text-align: left;
                                vertical-align: top;
                                border-top: 0px;
                                border-right: 0px;
                                border-bottom: 0px;
                                border-left: 0px;
                                "
                            >
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                >
                                <tbody>
                                    <tr>
                                    <td>
                                        <div></div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                            </td>
                            </tr>
                        </tbody>
                        </table>
                    </td>
                    </tr>
                </tbody>
                </table>
                <table
                align="center"
                width="100%"
                border="0"
                cellpadding="0"
                cellspacing="0"
                role="presentation"
                >
                <tbody>
                    <tr>
                    <td>
                        <table
                        class="m_-3509855705363049637row-content m_-3509855705363049637stack"
                        align="center"
                        border="0"
                        cellpadding="0"
                        cellspacing="0"
                        role="presentation"
                        style="background-color: #fffff; color: #000000; width: 700px"
                        width="700"
                        >
                        <tbody>
                            <tr>
                            <td
                                class="m_-3509855705363049637column"
                                width="100%"
                                style="
                                font-weight: 400;
                                text-align: left;
                                vertical-align: top;
                                padding-top: 5px;
                                padding-bottom: 5px;
                                border-top: 0px;
                                border-right: 0px;
                                border-bottom: 0px;
                                border-left: 0px;
                                "
                            >
                                <table
                                width="100%"
                                border="0"
                                cellpadding="0"
                                cellspacing="0"
                                role="presentation"
                                >
                                <tbody>
                                    <tr>
                                    <td>
                                        <div></div>
                                    </td>
                                    </tr>
                                </tbody>
                                </table>
                            </td>
                            </tr>
                        </tbody>
                        </table>
                    </td>
                    </tr>
                </tbody>
                </table>
            </td>
            </tr>
        </tbody>
        </table>
    """
