import numpy as np
from utils.steganography_lsb import (
    PAYLOAD_BITS,
    build_payload,
    embed_lsb_payload,
    extract_lsb_payload,
)


def test_lsb_roundtrip():
    img = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
    bits = build_payload()
    stego = embed_lsb_payload(img, bits)
    recovered = extract_lsb_payload(stego, PAYLOAD_BITS)
    assert recovered == bits


def test_embedding_formula():
    img = np.array([[170]], dtype=np.uint8)  # 10101010
    bits = [1]
    stego = embed_lsb_payload(img, bits)
    assert stego[0, 0] == 171  # 10101011
