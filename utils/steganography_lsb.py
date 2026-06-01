# utils/steganography_lsb.py
"""Spatial-domain LSB steganography utilities.

Implements the steganographic embedding described in the research paper:
  p̃_k = (p_k & 0xFE) | b_k

The structured payload is: 32-char UUID + 25-char ISO 8601 timestamp + 64-char SHA-256 hex
= 121 characters = 968 bits.
"""

import hashlib
import uuid
from datetime import UTC, datetime

import numpy as np

PAYLOAD_BITS = 968  # 121 chars × 8 bits


def build_payload(
    uuid_str: str | None = None,
    timestamp: str | None = None,
    checksum: str | None = None,
) -> list[int]:
    """Build the 968-bit structured LSB payload.

    Args:
        uuid_str: 32-character document UUID. Auto-generated if None.
        timestamp: ISO 8601 timestamp (25 chars). Auto-generated if None.
        checksum: SHA-256 hex checksum (64 chars). Auto-generated if None.

    Returns:
        List of 968 integers, each 0 or 1.
    """
    if uuid_str is None:
        uuid_str = uuid.uuid4().hex  # 32 chars
    if timestamp is None:
        timestamp = datetime.now(UTC).isoformat()[:25]  # 25 chars
    if checksum is None:
        checksum = hashlib.sha256(uuid_str.encode()).hexdigest()  # 64 chars

    payload_str = uuid_str[:32] + timestamp[:25] + checksum[:64]  # 121 chars
    bits = []
    for char in payload_str:
        byte_val = ord(char)
        for bit_pos in range(7, -1, -1):  # big-endian
            bits.append((byte_val >> bit_pos) & 1)
    return bits  # 968 bits


def embed_lsb_payload(image: np.ndarray, payload_bits: list[int]) -> np.ndarray:
    """Embed payload bits into the LSB of image pixels using sequential raster scan.

    Formula: p̃_k = (p_k & 0xFE) | b_k

    Args:
        image: Greyscale image as 2-D numpy array (dtype uint8).
        payload_bits: List of bits (0 or 1) to embed. Length must be <= image.size.

    Returns:
        New numpy array with payload embedded (same shape and dtype as input).
    """
    stego = image.copy().astype(np.uint8)
    flat = stego.flatten()
    for k, bit in enumerate(payload_bits):
        flat[k] = (flat[k] & 0xFE) | int(bit)
    return flat.reshape(image.shape)


def extract_lsb_payload(image: np.ndarray, n_bits: int = PAYLOAD_BITS) -> list[int]:
    """Extract LSB payload bits from image pixels using sequential raster scan.

    Args:
        image: Greyscale image as 2-D numpy array (dtype uint8).
        n_bits: Number of bits to extract (default 968).

    Returns:
        List of extracted bits (0 or 1), length n_bits.
    """
    flat = image.flatten().astype(np.uint8)
    return [int(flat[k]) & 1 for k in range(n_bits)]


def bits_to_string(bits: list[int]) -> str:
    """Convert a list of bits back to a string (big-endian, 8 bits per char).

    Args:
        bits: List of bits (0 or 1). Length must be a multiple of 8.

    Returns:
        Decoded string.
    """
    chars = []
    for i in range(0, len(bits), 8):
        byte_bits = bits[i : i + 8]
        if len(byte_bits) < 8:
            break
        byte_val = 0
        for b in byte_bits:
            byte_val = (byte_val << 1) | b
        try:
            chars.append(chr(byte_val))
        except (ValueError, OverflowError):
            chars.append("?")
    return "".join(chars)
