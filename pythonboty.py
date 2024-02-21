import datetime
import logging
import os
import smtplib
import pdfkit
import smtplib
import io
import pdfkit
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from telegram import Update, ReplyKeyboardRemove
from email import encoders
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
import time
import random
import asyncio

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# Define conversation states
NAME, EMAIL, PASSWORD, SUBJECT, BODY, HTML_FILE, RECIPIENTS = range(7)


AUTHORIZED_CHAT_IDS = [858971473, 2082378529]  # Example chat IDs of authorized users

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_chat_id = update.effective_chat.id
    if user_chat_id in AUTHORIZED_CHAT_IDS:
        await update.message.reply_text(
            "Hi! I'm the Email Sender bot. Let's set up your email.\n\n"
            "Please enter your name."
        )
        return NAME
    else:
        await update.message.reply_text(
            "fuck you..u dont have access."
        )
        return ConversationHandler.END  # Ends the conversation if the user is not authorized

# Define NAME as a state for the conversation handler (usually at the start of your script)
NAME = 0



async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Here's how you can use this bot:\n\n"
        "/start - Start the conversation and set up your email.\n"
        "/help - Get this help message.\n\n"
        "Follow the prompts to enter your name, email address, password, "
        "email subject, and upload an HTML file for the email content. "
        "Finally, upload a text file with recipient email addresses, each on a new line.\n\n"
        "Your password is handled securely and is not stored. "
        "Make sure the HTML and recipient list files are correctly formatted."
    )
    await update.message.reply_text(help_text)

def clear_user_data(context: ContextTypes.DEFAULT_TYPE):
    """
    Clears user-specific sensitive data after use or cancellation.
    """
    user_data_keys = ["name", "email", "password", "subject", "body", "html_content"]
    for key in user_data_keys:
        if key in context.user_data:
            del context.user_data[key]


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Please enter your email address.")
    return EMAIL


async def email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["email"] = update.message.text
    await update.message.reply_text("Please enter your password.")
    return PASSWORD


async def password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["password"] = update.message.text
    await update.message.reply_text("Please enter the email subject.")
    return SUBJECT


async def subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["subject"] = update.message.text
    await update.message.reply_text("Please enter the email body content.")
    return BODY


async def body(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["body"] = update.message.text
    await update.message.reply_text(
        "Please upload the HTML file for the email content."
    )
    return HTML_FILE


async def html_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    file_received = update.message.document
    if file_received:
        file_info = await context.bot.get_file(file_received.file_id)
        file_content = await file_info.download_as_bytearray()
        context.user_data["html_content"] = file_content.decode("utf-8")
        await update.message.reply_text(
            "HTML file received successfully. Please upload the recipients' text file."
        )
        return RECIPIENTS
    else:
        await update.message.reply_text("No file received. Please upload a file.")
        return HTML_FILE


async def recipients(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    file_received = update.message.document
    if file_received:
        file_info = await context.bot.get_file(file_received.file_id)
        file_content = await file_info.download_as_bytearray()
        recipient_emails = file_content.decode("utf-8").split("\n")
        batch_size = 100
        email_batches = [
            recipient_emails[i : i + batch_size]
            for i in range(0, len(recipient_emails), batch_size)
        ]

        # Send initial message and save its message_id for updates
        status_message = await update.message.reply_text("Starting to send emails...")
        for batch in email_batches:
            await send_email(context, update, batch, status_message.message_id)
            await asyncio.sleep(1)  # Add delay between batches as needed

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=status_message.message_id,
            text="Emails have been sent successfully.",
        )
        clear_user_data(context)
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "Invalid file format. Please upload a text file (.txt)."
        )
        return RECIPIENTS


def setup_smtp_server():
    """
    Setup and return an SMTP server object.
    """
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()  # Upgrade the connection to secure
    return server


async def send_email(
    context: ContextTypes.DEFAULT_TYPE,
    update: Update,
    recipient_emails,
    status_message_id,
):
    """
    Send emails to a list of recipients and handle errors and disconnections, with updates to Telegram.
    """
    sender_email = context.user_data["email"]
    password = context.user_data["password"]
    html_content = context.user_data["html_content"]
    subject = context.user_data["subject"]
    sender_name = context.user_data["name"]
    failed_recipients = []

    # Attempt to setup SMTP server and login
    try:
        server = setup_smtp_server()
        server.login(sender_email, password)
    except Exception as e:
        logger.error(f"SMTP setup or login failed: {e}")
        return
    
    original_html_content = html_content

    for recipient_email in recipient_emails:
        
        try:
            msg = MIMEMultipart()
            msg["From"] = f"{sender_name} <{sender_email}>"
            msg["To"] = recipient_email
            strrand = str(random.randint(10000, 99999))
            msg["Subject"] = subject +' invoice: '+strrand

            # Body text
            '''
            # Example list of text lines
            body_lines = [
                "Hi toxxx, just a heads-up that we've charged your account for your recent purchase. See the attached invoice id profileidxx for more details. Thanks for your continued support!.",
                "Greetings toxxx, your latest transaction with us has been charged. Please refer to the attached invoice id profileidxx for full details. Should you need assistance, we're here to help!.",
                "Hello toxxx, we've successfully processed your purchase and applied the charge to your account. Detailed information is available in the attached invoice id profileidxx. Thank you for choosing us!.",
                "toxxx, just letting you know that we've billed your recent purchase. Check out the attached invoice id profileidxx for all the details. Thanks for shopping with us!.",
                "Hello toxxx, your account has been charged for your latest purchase. For invoice id profileidxx , please see the attached document . We're here if you need any help!.",
                "Hi toxxx, we've charged your account as per your recent purchase. The invoice id profileidxx is attached for your convenience. Thank you for your patronage!.",
                "Greetings toxxx, your recent transaction has been processed, and your account has been charged accordingly. Please find your invoice id profileidxx attached for the details. We're grateful for your trust in us.!",
                "toxxx, we've issued an invoice id profileidxx for your recent purchase and the charge has been processed. For more information, please check the attached invoice. Should you have any inquiries, our customer service is here for you.",
                "toxxx, your recent purchase details and the corresponding charge have been compiled in your latest invoice id profileidxx. For a detailed breakdown, please see the attached file. We appreciate your business!.",
                "Dear toxxx, we've completed processing your latest order and the charge has been made. You can find your attached invoice id profileidxx . Any questions? Our team is ready to assist you."

            ]
            body = random.choice(body_lines)
            '''
            #body = 'You can check the details attached here'
            body_content = context.user_data.get("body", "")
            
            body = str(body_content)
            body = body.replace('toxxx', recipient_email).replace('profileidxx', strrand)
            msg.attach(MIMEText(body, "plain"))

            # Convert HTML to PDF
            personalized_html_content = original_html_content.replace('toxxx', recipient_email).replace('forxxx', recipient_email).replace('profileidxx', strrand)
            pdf_file_path = "temp_emakjkil_content.pdf"
            pdfkit.from_string(personalized_html_content, pdf_file_path)

            # Attach the PDF
            with open(pdf_file_path, "rb") as pdf_file:
                attachment = MIMEApplication(pdf_file.read(), _subtype="pdf")
            attachment.add_header('Content-Disposition', f'attachment; filename="{pdf_file_path}"')
            msg.attach(attachment)

            # Send the email
            server.send_message(msg)
            '''
            msg = MIMEMultipart()
            msg["From"] = f"{sender_name} <{sender_email}>"
            msg["To"] = recipient_email
            strrand = str(random.randint(10000, 99999))
            personalized_html_content = original_html_content.replace('toxxx', msg["To"]).replace('forxxx', msg["To"]).replace('profileidxx',strrand)
            #html_content = html_content.replace('toxxx',msg["To"]).replace('forxxx',msg["To"]).replace('profileidxx','gghghhg')
            msg["Subject"] = subject
            msg.attach(MIMEText(personalized_html_content, "html"))
            server.send_message(msg)
            '''
            logger.info(f"Email sent to {recipient_email}")

            # Update the Telegram message with the current status
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            update_text = f"Sending email to: {recipient_email} at {timestamp}"
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_message_id,
                text=update_text,
            )

        except smtplib.SMTPServerDisconnected:
            logger.error(
                f"Connection lost with SMTP server. Attempting to reconnect and resend to {recipient_email}"
            )
            time.sleep(5)  # Wait before retrying
            try:
                server = setup_smtp_server()
                server.login(sender_email, password)
                server.send_message(
                    msg
                )  # Attempt to resend the message after reconnection
                logger.info(f"Email resent to {recipient_email} after reconnection.")
            except Exception as retry_error:
                logger.error(
                    f"Failed to resend email to {recipient_email}: {retry_error}"
                )
                failed_recipients.append(recipient_email)
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}")
            failed_recipients.append(recipient_email)

    try:
        server.quit()
    except smtplib.SMTPServerDisconnected:
        logger.error("Server disconnected on quit.")

    # Handle failed_recipients by sending a summary to the Telegram chat
    if failed_recipients:
        failed_text = (
            "Failed to send emails to the following recipients:\n"
            + "\n".join(failed_recipients)
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=failed_text
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="All emails were sent successfully."
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Setup cancelled.", reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END


def main() -> None:
    application = (
        Application.builder()
        .token("6661419442:AAG8EtbIThWRbJvgJRGidD95fJY-usitp7E")
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, email)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password)],
            SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, subject)],
            HTML_FILE: [MessageHandler(None, html_file)],
            BODY: [MessageHandler(None, body)],
            RECIPIENTS: [MessageHandler(None, recipients)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))

    application.run_polling()


if __name__ == "__main__":
    main()
