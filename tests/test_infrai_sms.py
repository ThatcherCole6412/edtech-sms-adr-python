from infrai_sms import Envelope, InfraiError


def test_envelope_error_is_explicit() -> None:
    envelope = Envelope.model_validate(
        {
            "ok": False,
            "data": None,
            "error": {"code": "INVALID_ARGUMENT", "message": "bad request"},
            "metadata": {},
        }
    )

    try:
        if not envelope.ok:
            raise InfraiError(envelope.error["code"], envelope.error, 400)
    except InfraiError as exc:
        assert exc.code == "INVALID_ARGUMENT"
        assert exc.status_code == 400
    else:
        raise AssertionError("expected InfraiError")
