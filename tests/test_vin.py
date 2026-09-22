from VinGenerator.vin import getCheckSumChar, getRandomVin


def test_checksum_returns_x():
    vin = "3P3ES47Y1XHMTPGGR"

    resultado = getCheckSumChar(vin)

    assert resultado == "X"


def test_generated_vin_has_17_characters():
    vin = getRandomVin()

    assert len(vin) == 17


def test_generated_vin_is_string():
    vin = getRandomVin()

    assert isinstance(vin, str)