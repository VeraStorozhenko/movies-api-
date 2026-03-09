from app.services.chat_service import parse_incoming_message


def test_parse_incoming_message_json_payload():
    text, recipient = parse_incoming_message('{"msg":"hello","to":"bob"}')
    assert text == "hello"
    assert recipient == "bob"


def test_parse_incoming_message_plain_text():
    text, recipient = parse_incoming_message("/w sam hi")
    assert text == "hi"
    assert recipient == "sam"
