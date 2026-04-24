"""
order_confirmation_service.py
SQS-based order confirmation email service.
Polls an SQS queue for new orders and sends confirmation emails via SMTP.
"""

import boto3
import smtplib
from email.mime.text import MIMEText

QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789/order-confirmations"
SMTP_HOST = "smtp.example.com"
SMTP_PORT = 587
SMTP_USER = "orders@example.com"
SMTP_PASS = "secret"


def get_sqs_client():
    return boto3.client("sqs", region_name="us-east-1")


def send_confirmation(order):
    """Send a confirmation email for the given order dict."""
    msg = MIMEText(f"Thank you for your order #{order['order_id']}!")
    msg["Subject"] = f"Order Confirmation #{order['order_id']}"
    msg["From"] = SMTP_USER
    msg["To"] = order["email"]

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [order["email"]], msg.as_string())


def process_messages():
    sqs = get_sqs_client()

    while True:
        response = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20,
        )

        messages = response.get("Messages", [])
        if not messages:
            continue

        for message in messages:
            # BUG 1: eval() on untrusted input -- arbitrary code execution risk
            order = eval(message["Body"])

            # BUG 2: delete-before-confirm -- message is deleted even if send fails
            sqs.delete_message(
                QueueUrl=QUEUE_URL,
                ReceiptHandle=message["ReceiptHandle"],
            )

            # BUG 3: no idempotency -- reprocessing sends duplicate emails
            # BUG 4: no retry -- transient SMTP errors silently drop the order
            # BUG 5: no DLQ routing -- poison-pill messages loop forever
            send_confirmation(order)


if __name__ == "__main__":
    process_messages()
