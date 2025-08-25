from twilio.rest import Client
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv('config.env')

# Twilio credentials
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')

# Initialize Twilio client
client = Client(account_sid, auth_token)

def make_phone_call(to_number, message):
    """
    Make a phone call using Twilio
    :param to_number: Recipient's phone number (format: +1234567890)
    :param message: Message to be read during the call
    """
    try:
        call = client.calls.create(
            twiml=f'<Response><Say>{message}</Say></Response>',
            to=to_number,
            from_=twilio_phone_number
        )
        print(f"Call initiated! Call SID: {call.sid}")
        return call.sid
    except Exception as e:
        print(f"Error making call: {str(e)}")
        return None

if __name__ == "__main__":
    # Example usage
    recipient_number = input("Enter the recipient's phone number (format: +1234567890): ")
    message_to_say = input("Enter the message to be read during the call: ")
    
    make_phone_call(recipient_number, message_to_say) 