from mailpit.client.api import API
from pytest_bdd import parsers, then


@then(parsers.parse('a confirmation email should be sent to "{email_address}"'))
def a_confirmation_email_should_be_sent_to(mailpit_api: API, email_address: str) -> None:
    # pytest.mark.parametrize doesn't play well with pytest-bdd, hence the line below
    mailpit_api.mailpit_url = "http://mailpit:8025"

    messages = mailpit_api.get_messages()
    assert messages.total == 1

    message = messages.messages[0]
    assert len(message.to) == 1
    assert message.to[0].address == email_address
